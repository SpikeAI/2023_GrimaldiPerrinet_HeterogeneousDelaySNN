#!/usr/bin/env python3
"""Build the GitHub Pages page of the notebook and keep its tables aligned.

The repository publishes ``FastMotionDetection.ipynb`` as a single, self-contained
HTML page named ``index.html``, which GitHub Pages serves at
https://spikeai.github.io/2023_GrimaldiPerrinet_HeterogeneousDelaySNN/ from the
``gh-pages`` branch. The page is produced by ``jupyter nbconvert --to html``, which
brings two flaws that this module repairs:

1. The Jupyter theme sets ``table-layout: fixed`` on rendered markdown tables while
   leaving their width ``auto``. The browser then sizes the columns from the widest
   unbreakable content of the table (here the MathJax boxes), so the columns no
   longer line up with their header. The fix gives the table a definite width and
   sets explicit ``<col>`` widths, which makes the column boundaries deterministic.
2. The page must be committed on an orphan branch, which is awkward to do from the
   branch that holds the sources. A dedicated worktree (``.gh-pages``) is used
   instead, so that the working branch is never checked out again.

The layout fix is idempotent: it is delimited by markers, so rebuilding the page
replaces the previous fix rather than stacking a new one.

Usage (from the repository, usually through ``make html`` and ``make docs``)::

    jupyter nbconvert --to html FastMotionDetection.ipynb \
        --output index.html --output-dir build/html   # nbconvert does not run the cells
    python build_docs.py build/html/index.html            # apply the layout fix
    python build_docs.py build/html/index.html --publish  # commit and push on gh-pages
    python build_docs.py --check --online                 # audit the Pages setup
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_NAME = "2023_GrimaldiPerrinet_HeterogeneousDelaySNN"
SITE_URL = f"https://spikeai.github.io/{REPO_NAME}/"
NOTEBOOK = "FastMotionDetection.ipynb"
BRANCH = "gh-pages"
TARGET = "index.html"
WORKTREE = ".gh-pages"
TIMEOUT_SECONDS = 20.0  # network timeout used by --online, in seconds

# Header of the table of variables, as written in the notebook.
VARIABLES_TABLE_HEADERS = ("Symbol", "Name in the code", "Default value", "Role")
# Width of each of its columns, in percent of the content width. Chosen so that the
# widest cell of every column fits on one or two lines: the symbols are short, the
# roles are sentences.
COLUMN_WIDTHS_PERCENT = (11, 19, 25, 45)

BEGIN_FIX = "<!-- begin build_docs.py layout fix -->"
END_FIX = "<!-- end build_docs.py layout fix -->"

LAYOUT_FIX_TEMPLATE = BEGIN_FIX + """
<style id="build-docs-layout">
/*
 * Layout fix for the tables of the rendered notebook.
 *
 * The Jupyter theme applies `table-layout: fixed` to `.jp-RenderedHTMLCommon table`
 * but leaves `width: auto`, so the browser distributes the width of the table
 * between the columns using the shrink-to-fit content of the table as a whole. A
 * table mixing text and MathJax boxes (which are inline blocks and thus cannot
 * wrap) ends up with one oversized column and headers that no longer match the
 * cells. A definite width, together with the explicit <col> widths inserted by
 * build_docs.py, restores a stable grid.
 */
.jp-RenderedMarkdown table {
  width: 100%;
  table-layout: fixed;
  margin-left: 0;
  margin-right: 0;
}
/* Keep long runs of code or of url inside their own column. */
.jp-RenderedMarkdown table td,
.jp-RenderedMarkdown table th {
  overflow-wrap: anywhere;
}
/* The cells are left aligned, so the headers sit above them instead of
 * floating in the middle of the column. */
.jp-RenderedMarkdown table th {
  text-align: left;
}
</style>
""" + END_FIX

_TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table>", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def run_git(*args, cwd):
    """Run a git command and return the completed process.

    Args:
        *args: Arguments of the ``git`` command, excluding the program name.
        cwd (pathlib.Path): Directory in which git is run.

    Returns:
        subprocess.CompletedProcess: Result of the command, with ``stdout`` and
        ``stderr`` decoded as text. Never raises: the caller decides what a
        non-zero return code means.
    """
    return subprocess.run(
        ("git", *args), cwd=str(cwd), capture_output=True, text=True, check=False
    )


def repository_of(path):
    """Return the root of the git repository containing ``path``.

    Args:
        path (pathlib.Path): Existing file or directory inside a working tree.

    Returns:
        pathlib.Path: Absolute path of the repository root.

    Raises:
        RuntimeError: If ``path`` is not inside a git working tree.
    """
    result = run_git("rev-parse", "--show-toplevel", cwd=Path(path).parent)
    if result.returncode != 0:
        raise RuntimeError(f"{path} is not in a git working tree: {result.stderr.strip()}")
    return Path(result.stdout.strip())


def _text(fragment):
    """Strip the HTML tags of a fragment and collapse the whitespace.

    Args:
        fragment (str): HTML of one or more table cells.

    Returns:
        str: Plain text of the fragment.
    """
    return " ".join(_TAG_RE.sub(" ", fragment).split())


def _row_cells(row_html):
    """Return the plain text of the cells of one table row.

    Args:
        row_html (str): HTML of a ``<tr>`` element.

    Returns:
        list of str: Text of each ``<th>`` or ``<td>``, in document order.
    """
    return [_text(cell) for cell in re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", row_html, re.DOTALL)]


def _write_atomic(path, text):
    """Write ``text`` to ``path`` through a temporary file, so that a reader never sees a partial page.

    Args:
        path (pathlib.Path): File to write.
        text (str): Content to write.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def markdown_tables(markdown):
    """Return the blocks of markdown table rows of a markdown document.

    Args:
        markdown (str): Markdown source of a notebook cell.

    Returns:
        list of list of str: One list of raw lines per contiguous table block.
    """
    blocks = []
    current = []
    for line in markdown.splitlines():
        if line.strip().startswith("|"):
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def check_notebook_tables(notebook_path=NOTEBOOK):
    """Report the malformed rows of the markdown tables of the notebook.

    A row is malformed when it does not have as many cells as the header of its
    table or when one of its cells is empty, which is what makes a column look
    ragged once rendered.

    Args:
        notebook_path (str or pathlib.Path): Notebook to inspect.

    Returns:
        list of str: One message per problem found, empty when all the tables are sound.
    """
    cells = json.loads(Path(notebook_path).read_text(encoding="utf-8"))["cells"]
    name = Path(notebook_path).name
    problems = []
    for index, cell in enumerate(cells):
        if cell.get("cell_type") != "markdown":
            continue
        source = "".join(cell.get("source", []))
        for block in markdown_tables(source):
            n_columns = len(_split_markdown_row(block[0]))
            for line in block:
                row = _split_markdown_row(line)
                if _is_separator_row(row):
                    continue
                if len(row) != n_columns:
                    problems.append(
                        f"{name} cell {index}: {len(row)} cells "
                        f"instead of {n_columns}: {line.strip()[:70]}"
                    )
                for position, value in enumerate(row, start=1):
                    if not value:
                        problems.append(
                            f"{name} cell {index}: empty cell "
                            f"{position}/{n_columns} of row: {line.strip()[:70]}"
                        )
    return problems


def _split_markdown_row(line):
    """Split one markdown table line into the plain text of its cells.

    Args:
        line (str): Raw markdown line, for example ``| $N_T$ | `N_T` | 200 | role |``.

    Returns:
        list of str: Text of each cell, stripped. Escaped pipes (``\\|``) are kept as text.
    """
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [re.sub(r"\\\|", "|", cell).strip() for cell in re.split(r"(?<!\\)\|", stripped)]


def _is_separator_row(cells):
    """Tell whether the cells of a markdown row form the header separator (``|---|:--|``).

    Args:
        cells (list of str): Cells of a markdown table row.

    Returns:
        bool: True when every cell is made of dashes and optional alignment colons.
    """
    return bool(cells) and all(re.fullmatch(r":?-{1,}:?", cell) for cell in cells)


def inject_layout_fix(html):
    """Insert (or refresh) the CSS which gives the tables a definite width.

    Args:
        html (str): HTML produced by ``jupyter nbconvert --to html``.

    Returns:
        str: HTML with the layout fix, once and only once, just before ``</head>``.
    """
    html = strip_layout_fix(html)
    if "</head>" not in html:
        raise RuntimeError("the HTML has no </head> element: is it a notebook page?")
    return html.replace("</head>", LAYOUT_FIX_TEMPLATE + "\n</head>", 1)


def strip_layout_fix(html):
    """Remove a previously injected layout fix, if any.

    Args:
        html (str): HTML of the rendered notebook.

    Returns:
        str: HTML without the delimited layout fix.
    """
    # The whitespace which follows the closing marker belonged to the injection, so
    # it is removed as well: that is what makes build() idempotent, hence a rebuild
    # of an unchanged notebook produces a byte-identical page and no new commit.
    return re.sub(
        re.escape(BEGIN_FIX) + r".*?" + re.escape(END_FIX) + r"[ \t]*\n?",
        "",
        html,
        flags=re.DOTALL,
    )


def column_groups(html):
    """Add explicit ``<col>`` widths to the tables whose header is the table of variables.

    ``table-layout: fixed`` honours the widths of ``<col>`` elements, so the columns
    of the annotated tables keep the same boundaries in the header and in the body,
    whatever the width of the window.

    Args:
        html (str): HTML of the rendered notebook.

    Returns:
        str: HTML in which each matching ``<table>`` has a ``<colgroup>`` as first child.
    """
    colgroup = "<colgroup>" + "".join(
        f'<col style="width: {width}%" />' for width in COLUMN_WIDTHS_PERCENT
    ) + "</colgroup>"
    columns = tuple(COLUMN_WIDTHS_PERCENT)
    if sum(columns) != 100:
        raise ValueError(f"COLUMN_WIDTHS_PERCENT must sum to 100, got {columns}")

    def annotate(match):
        table = match.group(0)
        if "<colgroup" in table:
            return table
        rows = re.findall(r"<tr\b[^>]*>.*?</tr>", table, re.DOTALL)
        if not rows:
            return table
        if tuple(_row_cells(rows[0])) != VARIABLES_TABLE_HEADERS:
            return table
        opening = re.match(r"<table\b[^>]*>", table).group(0)
        return opening + colgroup + table[len(opening):]

    return _TABLE_RE.sub(annotate, html)


def build(source, destination=None):
    """Apply the layout fix to a rendered notebook page.

    Args:
        source (str or pathlib.Path): HTML page generated by nbconvert.
        destination (str or pathlib.Path or None): Where to write the fixed page.
            Defaults to ``source``, which is then rewritten in place.

    Returns:
        pathlib.Path: File which was written.
    """
    source = Path(source)
    destination = Path(destination) if destination is not None else source
    html = source.read_text(encoding="utf-8")
    fixed = column_groups(inject_layout_fix(html))
    _write_atomic(destination, fixed)
    return destination


def worktree_path(repo, branch=BRANCH, worktree=WORKTREE):
    """Return the path of the worktree hosting the Pages branch, creating it if needed.

    Args:
        repo (pathlib.Path): Root of the repository.
        branch (str): Branch served by GitHub Pages.
        worktree (str): Name of the directory holding that branch, relative to ``repo``.

    Returns:
        pathlib.Path: Absolute path of the worktree.

    Raises:
        RuntimeError: If neither a local branch, a remote branch, nor an existing
            worktree can be used to publish the page.
    """
    path = repo / worktree
    listing = run_git("worktree", "list", "--porcelain", cwd=repo).stdout
    for block in listing.split("\n\n"):
        fields = dict(
            line.split(" ", 1) for line in block.splitlines() if " " in line
        )
        if fields.get("worktree") == str(path):
            return path
    if run_git("rev-parse", "--verify", "--quiet", branch, cwd=repo).returncode == 0:
        result = run_git("worktree", "add", str(path), branch, cwd=repo)
    else:
        # Either the branch lives on the remote only -- fetch it without checking
        # which remote branch it is -- or the page has never been published, in
        # which case the branch starts empty so that the page does not inherit the
        # sources of the working branch.
        run_git("fetch", "origin", f"{branch}:{branch}", cwd=repo)
        if run_git("rev-parse", "--verify", "--quiet", branch, cwd=repo).returncode == 0:
            result = run_git("worktree", "add", str(path), branch, cwd=repo)
        else:
            result = run_git("worktree", "add", "--orphan", "-b", branch, str(path), cwd=repo)
    if result.returncode != 0:
        raise RuntimeError(
            f"cannot create the worktree {path} for the branch {branch}: "
            f"{result.stderr.strip()} "
            "(creating a first Pages branch needs git 2.49 or newer)"
        )
    return path


def publish(html, repo=None, branch=BRANCH, target=TARGET, worktree=WORKTREE, push=True):
    """Commit the rendered page on the Pages branch.

    Args:
        html (str): Content of the page.
        repo (pathlib.Path or None): Repository root; inferred from this file if None.
        branch (str): Branch served by GitHub Pages.
        target (str): Name of the file inside that branch.
        worktree (str): Directory holding the checkout of ``branch``.
        push (bool): Push the commit to ``origin``. The Pages branch is fetched
            first and updated only when the update is a fast-forward.

    Returns:
        str: One sentence describing what happened ("nothing to commit", commit hash, ...).
    """
    repo = Path(repo) if repo is not None else repository_of(Path(__file__))
    path = worktree_path(repo, branch=branch, worktree=worktree)
    head = run_git("-C", str(path), "symbolic-ref", "--short", "HEAD", cwd=repo)
    if head.stdout.strip() != branch:
        checkout = run_git("-C", str(path), "checkout", "-q", branch, cwd=repo)
        if checkout.returncode != 0:
            raise RuntimeError(
                f"the worktree {path} is not on the branch {branch}: {checkout.stderr.strip()}"
            )
    # Refresh the Pages branch before overwriting it, but only by fast-forward: a
    # branch which diverged from the remote must be reconciled by hand rather than
    # silently overwritten. FETCH_HEAD is used rather than ``git pull`` because the
    # worktree created by ``worktree add -B`` has no upstream for this branch.
    fetch = run_git("-C", str(path), "fetch", "--quiet", "origin", branch, cwd=repo)
    if fetch.returncode != 0:
        print(
            "warning: could not fetch "
            f"{branch}, keeping the local copy ({fetch.stderr.strip()})"
        )
    else:
        merge = run_git("-C", str(path), "merge", "--ff-only", "-q", "FETCH_HEAD", cwd=repo)
        if merge.returncode != 0:
            print(
                f"warning: {branch} diverged from origin, leaving it as it is "
                f"({merge.stderr.strip()})"
            )
    _write_atomic(path / target, html)
    run_git("-C", str(path), "add", "--", target, cwd=repo)
    if run_git("-C", str(path), "diff", "--cached", "--quiet", cwd=repo).returncode == 0:
        return f"{target} of branch {branch} is already up to date"
    sha = run_git("rev-parse", "--short", "HEAD", cwd=repo).stdout.strip()
    today = dt.date.today().isoformat()
    title = f"Update {target} from {NOTEBOOK}"
    body = f"Rendered from {NOTEBOOK} at {sha} on {today}."
    commit = run_git("-C", str(path), "commit", "-m", title, "-m", body, cwd=repo)
    if commit.returncode != 0:
        raise RuntimeError(f"cannot commit {target}: {commit.stderr.strip()}")
    revision = run_git("-C", str(path), "rev-parse", "--short", "HEAD", cwd=repo).stdout.strip()
    if not push:
        return f"committed {revision} on {branch} (not pushed)"
    pushed = run_git("-C", str(path), "push", "origin", f"HEAD:refs/heads/{branch}", cwd=repo)
    if pushed.returncode != 0:
        raise RuntimeError(f"cannot push {branch}: {pushed.stderr.strip()}")
    return f"published {revision} on {branch}"


def status(repo=None, notebook=NOTEBOOK, page=None, branch=BRANCH, online=False):
    """Audit the Pages setup and report every inconsistency found.

    Checks, in order: the markdown tables of the notebook, the local page (once
    built), the content of the Pages branch, and -- when ``online`` is True -- the
    page which GitHub Pages actually serves.

    Args:
        repo (pathlib.Path or None): Repository root; inferred from this file if None.
        notebook (str): Notebook whose tables are checked.
        page (str or pathlib.Path or None): Built page to inspect, if already built.
        branch (str): Branch served by GitHub Pages.
        online (bool): Fetch ``SITE_URL`` to compare the served page with the branch.

    Returns:
        list of str: Findings, one per line. An empty list means a sound setup.
    """
    repo = Path(repo) if repo is not None else repository_of(Path(__file__))
    findings = []
    findings += check_notebook_tables(repo / notebook)

    if page is not None and Path(page).exists():
        html = Path(page).read_text(encoding="utf-8")
        if BEGIN_FIX not in html:
            findings.append(f"{Path(page).name}: layout fix is missing, run `python build_docs.py {page}`")
        if "<colgroup" not in html:
            findings.append(f"{Path(page).name}: table of variables has no <colgroup>")
    else:
        findings.append(f"{page or 'build/html/' + TARGET} was not built, run `make html`")

    listing = run_git("ls-tree", "-r", "--name-only", branch, cwd=repo)
    if listing.returncode != 0:
        findings.append(f"branch {branch} is not available locally")
    else:
        names = listing.stdout.split()
        if TARGET not in names:
            findings.append(f"branch {branch} does not contain {TARGET}, so Pages has nothing to serve")
        blob = run_git("show", f"{branch}:{TARGET}", cwd=repo).stdout
        if BEGIN_FIX not in blob:
            findings.append(f"published {TARGET} still lacks the layout fix: run `make docs`")
        date = run_git("log", "-1", "--format=%cI", branch, cwd=repo).stdout.strip()
        print(f"branch {branch}: {TARGET} committed on {date}, {len(blob)} bytes")
        extra = sorted(set(names) - {TARGET})
        if extra:
            findings.append(f"branch {branch} holds unexpected files: {', '.join(extra)}")

    if online:
        try:
            with urllib.request.urlopen(SITE_URL, timeout=TIMEOUT_SECONDS) as response:
                served = response.read().decode("utf-8", "replace")
                print(f"{SITE_URL}: HTTP {response.status}, {len(served)} bytes")
        except (urllib.error.URLError, TimeoutError) as error:
            findings.append(f"{SITE_URL} is unreachable ({error})")
        else:
            if BEGIN_FIX not in served:
                findings.append("the served page lacks the layout fix: Pages serves an older commit")
    return findings


def main(argv=None):
    """Command line interface.

    Args:
        argv (list of str or None): Arguments, defaults to ``sys.argv[1:]``.

    Returns:
        int: 0 when everything is fine, 1 when a finding or an error remains.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("page", nargs="?", default=f"build/html/{TARGET}",
                        help=f"HTML page rendered from {NOTEBOOK} (default: %(default)s)")
    parser.add_argument("--publish", action="store_true",
                        help=f"commit the fixed page on the {BRANCH} branch")
    parser.add_argument("--no-push", action="store_true",
                        help=f"with --publish, commit on {BRANCH} without pushing")
    parser.add_argument("--check", action="store_true",
                        help="audit the notebook tables and the Pages setup instead of building")
    parser.add_argument("--online", action="store_true",
                        help=f"with --check, also fetch {SITE_URL}")
    parser.add_argument("--branch", default=BRANCH, help=f"Pages branch (default: {BRANCH})")
    parser.add_argument("--target", default=TARGET, help=f"page name inside {BRANCH} (default: {TARGET})")
    parser.add_argument("--worktree", default=WORKTREE,
                        help=f"directory hosting {BRANCH} (default: {WORKTREE})")
    options = parser.parse_args(argv)

    if options.check:
        findings = status(page=options.page, branch=options.branch, online=options.online)
        for finding in findings:
            print(f"- {finding}")
        if not findings:
            print(f"the Pages setup of {SITE_URL} is sound")
        return 1 if findings else 0

    try:
        page = build(options.page)
        print(f"fixed the table layout of {page}")
        if options.publish:
            print(publish(page.read_text(encoding="utf-8"), branch=options.branch,
                          target=options.target, worktree=options.worktree,
                          push=not options.no_push))
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
