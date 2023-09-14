"""
# 2023-09-14_video-abstract


 Using the template @ https://github.com/SpikeAI/2022_polychronies-review/blob/main/2022-12-23_video-abstract.py
and using that @ https://github.com/SpikeAI/2022-09_UltraFastCat/blob/main/Jeremie-etal-Vision_video-abstract.py

python 2023-09-14_video-abstract.py
cp 2023-09-14_HDSNN_video-abstract.mp4 /Users/laurentperrinet/quantic/blog/hugo_academic/content/publication/grimaldi-23-bc/

"""
# Creating the movie using the (*excellent*) [MoviePy](http://zulko.github.io/moviepy/index.html) library:

videoname = "2023-09-14_HDSNN_video-abstract"
gifname = videoname + ".gif"
gifname = None
fps = 30
from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip

H, W = 500, 800
H_fig, W_fig = int(H-H/(1.618*3)), int(W-W/(1.618*3))


opt_t = dict(font="Arial", size=(W,H), method='caption')
opt_st = dict(font="Arial", size=(W,H), method='caption')
# opt_t = dict(size=(W,H), method='caption')
# opt_st = dict(size=(W,H), method='caption')

clip = []
t = 0 

#################################################################################
# TITRE
#################################################################################
# 
texts = ["""Learning heterogeneous delays of spiking neurons for motion detection





         
""", """Learning heterogeneous delays of spiking neurons for motion detection


   Antoine Grimaldi and Laurent Udo Perrinet

   

""", """Learning heterogeneous delays of spiking neurons for motion detection


   Antoine Grimaldi and Laurent Udo Perrinet

   
Biological Cybernetics (2023)
"""]
txt_opts = dict(align='center', color='white', **opt_t) #stroke_color='gray', stroke_width=.5
duration = 1.5
for text in texts:
    txt = TextClip(text, fontsize=35, **txt_opts).set_start(t).set_duration(duration)
    t += duration
    clip.append(txt)

#################################################################################
# INTRO
#################################################################################

intro_subs = ["""The precise temporal structure of spiking neuronal
 
              
              
              
 
""", """The precise temporal structure of spiking neuronal
activity is thought to be important for the 
formation of efficient neural computations.



""", """The precise temporal structure of spiking neuronal
activity is thought to be important for the 
formation of efficient neural computations.
Here, we develop a novel algorithm for learning 
heterogeneous delays of spiking neurons and 
apply it to visual motion detection.
"""]

sub_opts = dict(fontsize=32, align='center', color='white', **opt_t)
sub_durations = [1.5, 1.5, 2.5]
for subtitle, sub_duration in zip(intro_subs, sub_durations):
    sub = TextClip(subtitle, **sub_opts).set_start(t).set_duration(sub_duration)
    t += sub_duration
    clip.append(sub)
clip.append(sub) # another bit on the last bit

#################################################################################
#################################################################################
chapters = [dict(title="Visual motion detection", color='green',
            content=[
                dict(figure='figures/2023-07-12_FastMotionDetection_input.mp4', duration=7, subtitle=[
                        "Visual motion detection consists in inferring the...", 
                        "...motion of a visual scene, for instance here of....", 
                        "...a natural image (left panel)."]),
                dict(figure='figures/2023-07-12_FastMotionDetection_input_1.mp4', duration=7, subtitle=[
                        "This motion is here modelled as a Levy flight, where...", 
                        "...the motion vector (red arrow in the middle panel)...", 
                        "...is selected at random, and the correponding...", 
                        "...'flight' is of random (Poisson) duration."]),
                dict(figure='figures/2023-07-12_FastMotionDetection_input_2.mp4', duration=7, subtitle=[
                        "We also model how the movie is transformed by an...", 
                        "...event-based camera (right panel) with ON (red)...", 
                        "...and OFF (blue) spikes. The problem is: how can...", 
                        "...we infer motion using only the observed spikes?"]),
                        ]), 
           dict(title="Emergence of spatio-temporal kernels", color='red',
            content=[
                dict(figure='figures/HDSNN_conv.png', duration=7, subtitle=[
                        "For this, we defined a traditional one-layered...", 
                        "...convolutional network which has the originality...", 
                        "...of using precise spike times as inputs...", 
                        "...and 3D kernels with heterogeneous delays which...", 
                        "...the structure of spiking motifs."]),
                dict(figure='figures/2023-07-12_FastMotionDetection_kernel.png', duration=7, subtitle=[
                        "This architecture is differentiable and can be...", 
                        "...trained in an unsupervised manner, yielding...", 
                        "...spatio-temporal kernels which ressemble those...", 
                        "...observed in neurobiology."]),
                        ]), 
           dict(title="Benchmarking on textures", color='orange',
            content=[
                dict(figure='figures/2023-07-12_FastMotionDetection_input-MC_0.mp4', duration=7, subtitle=[
                        "We first benchmarked our network on textured images...", 
                        "...which are often used in experiments and allow to...", 
                        "...titrate the role of visual parameters such as...", 
                        "...spatial frequency, motion or orientation."]),
                dict(figure='figures/2023-07-12_FastMotionDetection_motion_clouds.png', duration=5, subtitle=[
                        "Results show characteristic tuning curves for these...", 
                        "...and especially a drop of accuracy when the orientation...", 
                        "...is not perpendicular to motion, aka the 'aperture problem'."]),
                        ]), 
           dict(title="Results of the detection", color='blue',
            content=[
                # dict(figure='figures/2023-07-12_FastMotionDetection_conv_HD-SNN.png', duration=7, subtitle=[
                dict(figure='/Users/laurentperrinet/quantic/science/Polychronies/pyTERtorch/2023-06-09_BiolCybernetics/figures/2023-07-08_FastMotionDetection_conv_HD-SNN.png', duration=7, subtitle=[
                        "The output of the heterogeneous delays SNN (HD-SNN) is...", 
                        "...a stream of events transforming the input events (left)...", 
                        "...into events informing about the most likely motion (right)...", 
                        "...a very sparse and efficient representation."]),
                dict(figure='figures/2023-07-12_FastMotionDetection_accuracy.png', duration=7, subtitle=[
                        "Moreover, the HD kernels have many near-zero coefficients...", 
                        "...which may be pruned to reduce the number of computations.", 
                        "While the full network has an accuracy of approx 98%...", 
                        "...this accuracy is only slightly reduced when reducing...", 
                        "...by an order of magnitude of 600 (note the log-axis)."]),
                        ]), 
           ]


# http://zulko.github.io/moviepy/ref/VideoClip/VideoClip.html?highlight=compositevideoclip#textclip
txt_opts = dict(fontsize=65, bg_color='white', align='center', **opt_st)
sub_opts = dict(fontsize=28, align='South', color='white', **opt_st)

for chapter in chapters:
    duration = 1
    txt = TextClip(chapter['title'], color=chapter['color'], **txt_opts).set_start(t).set_duration(duration)
    t += duration
    clip.append(txt)

    for content in chapter['content']:
        # set the figure
        figname = content['figure']
        duration = content['duration']
        if figname[-4:]=='.mp4' :
            img = VideoFileClip(figname, audio=False)
            print(figname, '--> duration:', img.duration, ', fps:', img.fps)
            # duration = img.duration
        else:
            img = ImageClip(figname)
        
        H_clip, W_clip, three = img.get_frame(0).shape
        if H_clip/W_clip > H_fig/W_fig: # portrait-like
            img = img.resize(height=H_fig)
        else: # landscape-like
            img = img.resize(width=W_fig)

        img = img.set_duration(duration)
        img = img.set_start(t).set_pos('center')#.resize(height=H_fig, width=W_fig)

        t += duration
        clip.append(img)

        # write the subtitles
        t_sub = t - duration
        sub_duration = duration / len(content['subtitle'])
        for subtitle in content['subtitle']:
            sub = TextClip(subtitle, **sub_opts).set_start(t_sub).set_duration(sub_duration)
            t_sub += sub_duration
            clip.append(sub)

#################################################################################
#################################################################################


#################################################################################
# OUTRO
#################################################################################
texts = ["""
Overall, this manuscript presents the potential
of using precise spiking motifs to design




""",
"""
Overall, this manuscript presents the potential
of using precise spiking motifs to design
more efficient machine learning algorithms, 
that is, faster and more energy-frugal,


""",
"""
Overall, this manuscript presents the potential
of using precise spiking motifs to design
more efficient machine learning algorithms, 
that is, faster and more energy-frugal,
but also to better understand 
neurobiological processes and their disorders...
"""]

txt_opts = dict(fontsize=30, align='center', **opt_t)
duration = 3
for text in texts:
    txt = TextClip(text, color='white', **txt_opts).set_start(t).set_duration(duration)
    t += duration
    clip.append(txt)
    
# FIN
texts = ["""
For more info, and the full, open-sourced code... visit


""", """
For more info, and the full, open-sourced code... visit

https://laurentperrinet.github.io/publication/grimaldi-23-bc
""",
]

txt_opts = dict(align='center', **opt_t)
duration = 2.5
for text in texts:
    txt = TextClip(text, color='orange', fontsize=26, **txt_opts).set_start(t).set_duration(duration)
    t += duration
    clip.append(txt)    

# QRCODE
# brew install qrencode
# qrencode -o figures/qrcode.png -d 200 https://laurentperrinet.github.io/publication/grimaldi-23-bc
img = ImageClip('figures/qrcode.png').set_duration(duration)
img = img.resize(width=(W_fig*2)//3).set_start(t).set_pos('center')
clip.append(img)

#################################################################################
# COMPOSITING
#################################################################################

video = CompositeVideoClip(clip)
video.write_videofile(videoname + '.mp4', fps=fps)

if not(gifname is None):
    video.write_gif(gifname, fps=fps)
    from pygifsicle import optimize
    optimize(gifname)