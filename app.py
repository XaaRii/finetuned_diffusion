from diffusers import AutoencoderKL, UNet2DConditionModel, StableDiffusionPipeline, StableDiffusionImg2ImgPipeline, DPMSolverMultistepScheduler
import gradio as gr
import torch
from PIL import Image
import utils
import datetime
import time
import psutil
import random


start_time = time.time()
is_colab = utils.is_google_colab()
state = None
current_steps = 25

class Model:
    def __init__(self, name, path="", prefix=""):
        self.name = name
        self.path = path
        self.prefix = prefix
        self.pipe_t2i = None
        self.pipe_i2i = None

models = [
     Model("Midjourney v4 style", "prompthero/midjourney-v4-diffusion", "mdjrny-v4 style "),
     Model("Anything v3", "Linaqruf/anything-v3.0", ""),
     Model("Arcane", "nitrosocke/Arcane-Diffusion", "arcane style "),
     Model("Dreamlike Diffusion 1.0", "dreamlike-art/dreamlike-diffusion-1.0", "dreamlikeart "),
     Model("Archer", "nitrosocke/archer-diffusion", "archer style "),
     Model("Stable Diffusion 2.1", "stabilityai/stable-diffusion-2-1", ""),
     Model("Modern Disney", "nitrosocke/mo-di-diffusion", "modern disney style "),
     Model("Classic Disney", "nitrosocke/classic-anim-diffusion", "classic disney style "),
     Model("Loving Vincent (Van Gogh)", "dallinmackay/Van-Gogh-diffusion", "lvngvncnt "),
     Model("Wavyfusion", "wavymulder/wavyfusion", "wa-vy style "),
     Model("Analog Diffusion", "wavymulder/Analog-Diffusion", "analog style "),
     Model("Redshift renderer (Cinema4D)", "nitrosocke/redshift-diffusion", "redshift style "),
     Model("Waifu", "hakurei/waifu-diffusion"),
     Model("Pastel-mix", "andite/pastel-mix"),
     Model("Anything v4", "andite/anything-v4.0"),
     Model("Cyberpunk Anime", "DGSpitzer/Cyberpunk-Anime-Diffusion", "dgs illustration style "),
     Model("Elden Ring", "nitrosocke/elden-ring-diffusion", "elden ring style "),
     Model("TrinArt v2", "naclbit/trinart_stable_diffusion_v2"),
     Model("Spider-Verse", "nitrosocke/spider-verse-diffusion", "spiderverse style "),
     Model("Balloon Art", "Fictiverse/Stable_Diffusion_BalloonArt_Model", "BalloonArt "),
     Model("Tron Legacy", "dallinmackay/Tron-Legacy-diffusion", "trnlgcy "),
     Model("Pok??mon", "lambdalabs/sd-pokemon-diffusers"),
     Model("Pony Diffusion", "AstraliteHeart/pony-diffusion"),
     Model("Robo Diffusion", "nousr/robo-diffusion"),
     Model("Epic Diffusion", "johnslegers/epic-diffusion")
  ]

custom_model = None
if is_colab:
  models.insert(0, Model("Custom model"))
  custom_model = models[0]

last_mode = "txt2img"
current_model = models[1] if is_colab else models[0]
current_model_path = current_model.path

if is_colab:
  pipe = StableDiffusionPipeline.from_pretrained(
      current_model.path,
      torch_dtype=torch.float16,
      scheduler=DPMSolverMultistepScheduler.from_pretrained(current_model.path, subfolder="scheduler"),
      safety_checker= None
      )

else:
  pipe = StableDiffusionPipeline.from_pretrained(
      current_model.path,
      torch_dtype=torch.float16,
      scheduler=DPMSolverMultistepScheduler.from_pretrained(current_model.path, subfolder="scheduler")
      )
    
if torch.cuda.is_available():
  pipe = pipe.to("cuda")
  pipe.enable_xformers_memory_efficient_attention()

device = "GPU ????" if torch.cuda.is_available() else "CPU ????"

def error_str(error, title="Error"):
    return f"""#### {title}
            {error}"""  if error else ""

def update_state(new_state):
  global state
  state = new_state

def update_state_info(old_state):
  if state and state != old_state:
    return gr.update(value=state)

def custom_model_changed(path):
  models[0].path = path
  global current_model
  current_model = models[0]

def on_model_change(model_name):
  
  prefix = "Enter prompt. \"" + next((m.prefix for m in models if m.name == model_name), None) + "\" is prefixed automatically" if model_name != models[0].name else "Don't forget to use the custom model prefix in the prompt!"

  return gr.update(visible = model_name == models[0].name), gr.update(placeholder=prefix)

def on_steps_change(steps):
  global current_steps
  current_steps = steps

def pipe_callback(step: int, timestep: int, latents: torch.FloatTensor):
    update_state(f"{step}/{current_steps} steps")#\nTime left, sec: {timestep/100:.0f}")

def inference(model_name, prompt, guidance, steps, n_images=1, width=512, height=512, seed=0, img=None, strength=0.5, neg_prompt=""):

  update_state(" ")

  print(psutil.virtual_memory()) # print memory usage

  global current_model
  for model in models:
    if model.name == model_name:
      current_model = model
      model_path = current_model.path

  # generator = torch.Generator('cuda').manual_seed(seed) if seed != 0 else None
  if seed == 0:
    seed = random.randint(0, 2147483647)

  generator = torch.Generator('cuda').manual_seed(seed)

  try:
    if img is not None:
      return img_to_img(model_path, prompt, n_images, neg_prompt, img, strength, guidance, steps, width, height, generator, seed), f"Done. Seed: {seed}"
    else:
      return txt_to_img(model_path, prompt, n_images, neg_prompt, guidance, steps, width, height, generator, seed), f"Done. Seed: {seed}"
  except Exception as e:
    return None, error_str(e)

def txt_to_img(model_path, prompt, n_images, neg_prompt, guidance, steps, width, height, generator, seed):

    print(f"{datetime.datetime.now()} txt_to_img, model: {current_model.name}")

    global last_mode
    global pipe
    global current_model_path
    if model_path != current_model_path or last_mode != "txt2img":
        current_model_path = model_path

        update_state(f"Loading {current_model.name} text-to-image model...")

        if is_colab or current_model == custom_model:
          pipe = StableDiffusionPipeline.from_pretrained(
              current_model_path,
              torch_dtype=torch.float16,
              scheduler=DPMSolverMultistepScheduler.from_pretrained(current_model.path, subfolder="scheduler"),
              safety_checker= None
              )
        else:
          pipe = StableDiffusionPipeline.from_pretrained(
              current_model_path,
              torch_dtype=torch.float16,
              scheduler=DPMSolverMultistepScheduler.from_pretrained(current_model.path, subfolder="scheduler")
              )
          # pipe = pipe.to("cpu")
          # pipe = current_model.pipe_t2i

        if torch.cuda.is_available():
          pipe = pipe.to("cuda")
          pipe.enable_xformers_memory_efficient_attention()
        last_mode = "txt2img"

    prompt = current_model.prefix + prompt  
    result = pipe(
      prompt,
      negative_prompt = neg_prompt,
      num_images_per_prompt=n_images,
      num_inference_steps = int(steps),
      guidance_scale = guidance,
      width = width,
      height = height,
      generator = generator,
      callback=pipe_callback)

    # update_state(f"Done. Seed: {seed}")
    
    return replace_nsfw_images(result)

def img_to_img(model_path, prompt, n_images, neg_prompt, img, strength, guidance, steps, width, height, generator, seed):

    print(f"{datetime.datetime.now()} img_to_img, model: {model_path}")

    global last_mode
    global pipe
    global current_model_path
    if model_path != current_model_path or last_mode != "img2img":
        current_model_path = model_path

        update_state(f"Loading {current_model.name} image-to-image model...")

        if is_colab or current_model == custom_model:
          pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
              current_model_path,
              torch_dtype=torch.float16,
              scheduler=DPMSolverMultistepScheduler.from_pretrained(current_model.path, subfolder="scheduler"),
              safety_checker= None
              )
        else:
          pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
              current_model_path,
              torch_dtype=torch.float16,
              scheduler=DPMSolverMultistepScheduler.from_pretrained(current_model.path, subfolder="scheduler")
              )
          # pipe = pipe.to("cpu")
          # pipe = current_model.pipe_i2i
        
        if torch.cuda.is_available():
          pipe = pipe.to("cuda")
          pipe.enable_xformers_memory_efficient_attention()
        last_mode = "img2img"

    prompt = current_model.prefix + prompt
    ratio = min(height / img.height, width / img.width)
    img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    result = pipe(
        prompt,
        negative_prompt = neg_prompt,
        num_images_per_prompt=n_images,
        image = img,
        num_inference_steps = int(steps),
        strength = strength,
        guidance_scale = guidance,
        # width = width,
        # height = height,
        generator = generator,
        callback=pipe_callback)

    # update_state(f"Done. Seed: {seed}")
        
    return replace_nsfw_images(result)

def replace_nsfw_images(results):

    if is_colab:
      return results.images
      
    for i in range(len(results.images)):
      if results.nsfw_content_detected[i]:
        results.images[i] = Image.open("nsfw.png")
    return results.images

# css = """.finetuned-diffusion-div div{display:inline-flex;align-items:center;gap:.8rem;font-size:1.75rem}.finetuned-diffusion-div div h1{font-weight:900;margin-bottom:7px}.finetuned-diffusion-div p{margin-bottom:10px;font-size:94%}a{text-decoration:underline}.tabs{margin-top:0;margin-bottom:0}#gallery{min-height:20rem}
# """
with gr.Blocks(css="style.css") as demo:
    gr.HTML(
        f"""
            <div class="finetuned-diffusion-div">
              <div>
                <h1>Pawele Multi-Diffusion</h1>
              </div>
              <p>
               Demo for multiple fine-tuned Stable Diffusion models, trained on different styles, some better, some worse.
               You can also load custom models hosted on <a href="https://huggingface.co/">https://huggingface.co/</a> 
               {("</br>You can play around as much as you want, although keep in mind this is hosted on free resources on google colab and those may vary greatly in the future." if is_colab else "")}
              </p>
              <p>Don't know what to type in as prompts? You can get inspired on various sites (<a href="https://prompthero.com/openjourney-prompts">prompthero</a>, <a href="https://lexica.art/">Lexica.art</a>) or you can try tools for prompt generating (such as <a href="https://huggingface.co/spaces/Gustavosta/MagicPrompt-Stable-Diffusion">MagicPrompt</a>)</br>Also, by writing prompt in brackets "()", they will be more important (this also works for negative prompts!)</p>
              <p>With negative prompts, you can further impact the quality of images. You can check out some examples at the bottom.</p>
              <p>
               Another ???????? tip: check out the home pages of available models. By doing this, you can quickly check out what to expect from each model, what is it good for and most importantly how to use it properly.</br>
               Some models needs prefixes to work -> these are used automatically by default. Please don't use them again on your own, it could lead to unexpected results.
               Homepages of available models: <a href="https://huggingface.co/prompthero/midjourney-v4-diffusion">Midjourney v4 style</a>, <a href="https://huggingface.co/Linaqruf/anything-v3.0">Anything v3</a>, <a href="https://huggingface.co/nitrosocke/Arcane-Diffusion">Arcane</a>, <a href="https://huggingface.co/dreamlike-art/dreamlike-diffusion-1.0">Dreamlike Diffusion 1.0</a>, <a href="https://huggingface.co/nitrosocke/archer-diffusion">Archer</a>, <a href="https://huggingface.co/stabilityai/stable-diffusion-2-1">Stable Diffusion 2.1</a>, <a href="https://huggingface.co/nitrosocke/mo-di-diffusion">Modern Disney</a>, <a href="https://huggingface.co/nitrosocke/classic-anim-diffusion">Classic Disney</a>, <a href="https://huggingface.co/dallinmackay/Van-Gogh-diffusion">Van Gogh</a>, <a href="https://huggingface.co/wavymulder/wavyfusion">Wavyfusion</a>, <a href="https://huggingface.co/wavymulder/Analog-Diffusion">Analog Diffusion</a>, <a href="https://huggingface.co/nitrosocke/redshift-diffusion">Redshift renderer</a>, <a href="https://huggingface.co/hakurei/waifu-diffusion">Waifu</a>, <a href="https://huggingface.co/andite/pastel-mix">Pastel-mix (another anime-like)</a>, <a href="https://huggingface.co/andite/anything-v4.0">Anything v4</a>, <a href="https://huggingface.co/DGSpitzer/Cyberpunk-Anime-Diffusion">Cyberpunk Anime</a>, <a href="https://huggingface.co/nitrosocke/elden-ring-diffusion">Elden Ring</a>, <a href="https://huggingface.co/naclbit/trinart_stable_diffusion_v2">TrinArt v2</a>, <a href="https://huggingface.co/nitrosocke/spider-verse-diffusion">Spider-Verse</a>, <a href="https://huggingface.co/Fictiverse/Stable_Diffusion_BalloonArt_Model">Balloon Art</a>, <a href="https://huggingface.co/dallinmackay/Tron-Legacy-diffusion">Tron Legacy</a>, <a href="https://huggingface.co/lambdalabs/sd-pokemon-diffusers">Pok??mon</a>, <a href="https://huggingface.co/AstraliteHeart/pony-diffusion">Pony Diffusion</a>, <a href="https://huggingface.co/nousr/robo-diffusion">Robo Diffusion</a>, <a href="https://huggingface.co/johnslegers/epic-diffusion">Epic Diffusion</a>
              </p>
               Running on <b>{device}</b>{(" in a <b>Google Colab</b>. (This means you have to check out the colab page every once in a while due to random 'are you still there?' checks)" if is_colab else "")}
            </div>
        """
    )
    with gr.Row():
        
        with gr.Column(scale=55):
          with gr.Group():
              model_name = gr.Dropdown(label="Model", choices=[m.name for m in models], value=current_model.name)
              with gr.Box(visible=False) as custom_model_group:
                custom_model_path = gr.Textbox(label="Custom model path", placeholder="Path to model, e.g. nitrosocke/Arcane-Diffusion", interactive=True)
                gr.HTML("<div><font size='2'>Custom models have to be downloaded first, so give it some time.</font></div>")
              
              with gr.Row():
                prompt = gr.Textbox(label="Prompt", show_label=False, max_lines=2,placeholder="Enter prompt. Style applied automatically").style(container=False)
                generate = gr.Button(value="Generate").style(rounded=(False, True, True, False))


              # image_out = gr.Image(height=512)
              gallery = gr.Gallery(label="Generated images", show_label=False, elem_id="gallery").style(grid=[2], height="auto")
          
          state_info = gr.Textbox(label="State", show_label=False, max_lines=2).style(container=False)
          error_output = gr.Markdown()

        with gr.Column(scale=45):
          with gr.Tab("Options"):
            with gr.Group():
              neg_prompt = gr.Textbox(label="Negative prompt", placeholder="What to exclude from the image")

              n_images = gr.Slider(label="Images", value=1, minimum=1, maximum=4, step=1)

              with gr.Row():
                guidance = gr.Slider(label="Guidance scale", value=7.5, maximum=15)
                steps = gr.Slider(label="Steps", value=current_steps, minimum=2, maximum=75, step=1)

              with gr.Row():
                width = gr.Slider(label="Width", value=512, minimum=64, maximum=1024, step=8)
                height = gr.Slider(label="Height", value=512, minimum=64, maximum=1024, step=8)

              seed = gr.Slider(0, 2147483647, label='Seed (0 = random)', value=0, step=1)

          with gr.Tab("Image to image"):
              with gr.Group():
                image = gr.Image(label="Image", height=256, tool="editor", type="pil")
                strength = gr.Slider(label="Transformation strength", minimum=0, maximum=1, step=0.01, value=0.5)

    if is_colab:
        model_name.change(on_model_change, inputs=model_name, outputs=[custom_model_group, prompt], queue=False)
        custom_model_path.change(custom_model_changed, inputs=custom_model_path, outputs=None)
    # n_images.change(lambda n: gr.Gallery().style(grid=[2 if n > 1 else 1], height="auto"), inputs=n_images, outputs=gallery)
    steps.change(on_steps_change, inputs=[steps], outputs=[], queue=False)

    inputs = [model_name, prompt, guidance, steps, n_images, width, height, seed, image, strength, neg_prompt]
    outputs = [gallery, error_output]
    prompt.submit(inference, inputs=inputs, outputs=outputs)
    generate.click(inference, inputs=inputs, outputs=outputs)

    ex = gr.Examples([
        [models[9].name, "tiny cute and adorable kitten adventurer dressed in a warm overcoat with survival gear on a winters day", 7.5, 25],
        [models[2].name, "portrait of dwayne johnson", 7.0, 35],
        [models[7].name, "portrait of a beautiful alyx vance half life", 10, 25],
        [models[8].name, "Aloy from Horizon: Zero Dawn, half body portrait, smooth, detailed armor, beautiful face, illustration", 7.0, 30],
        [models[7].name, "fantasy portrait painting, digital art", 4.0, 20],
    ], inputs=[model_name, prompt, guidance, steps], outputs=outputs, fn=inference, cache_examples=False)
    
    gr.HTML("""
     If you have better example prompts, send them to Pawele and he will put it here (too lazy to come up with some good ones myself, sorry). 
    """)

    exNegative = gr.Examples([
        ["ugly, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, out of frame, extra limbs, disfigured, deformed, body out of frame, bad anatomy, watermark, signature, cut off, low contrast, underexposed, overexposed, bad art, beginner, amateur, distorted face"],
        ["grotesque, unsightly, misshapen, deformed, mangled, awkward, distorted, twisted, contorted, lopsided, malformed, asymmetrical, irregular, unnatural, botched, mutilated,disfigured, ugly, offensive, repulsive, revolting, ghastly, hideous, unappealing, terrible, awful, frightful, odious, loathsome, obnoxious, detestable, hateful, repugnant, sickening, vile, abhorrent, contemptible, execrable, repellent, disgusting, distasteful, abominable, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, outof frame, extra limbs, body out of frame, blurry, bad anatomy, blurred, watermark, grainy, signature, cut off, draft, amateur, multiple, gross, weird, uneven, furnishing, decorating, decoration, furniture, text, poor, low, basic, worst, juvenile, unprofessional, failure, crayon, Oil, nude, sex, label, thousand hands"],
    ], inputs=[neg_prompt], outputs=outputs, fn=inference, cache_examples=False)

    gr.HTML("""
    <div style="border-top: 1px solid #303030;">
      <br>
      <p>Models by <a href="https://huggingface.co/nitrosocke">@nitrosocke</a>, <a href="https://twitter.com/haruu1367">@haruu1367</a>, <a href="https://twitter.com/DGSpitzer">@Helixngc7293</a>, <a href="https://twitter.com/dal_mack">@dal_mack</a>, <a href="https://twitter.com/prompthero">@prompthero</a> and others. ??????</p>
      <p>This space uses the <a href="https://github.com/LuChengTHU/dpm-solver">DPM-Solver++</a> sampler by <a href="https://arxiv.org/abs/2206.00927">Cheng Lu, et al.</a>.</p>
      <p><img src="https://visitor-badge.glitch.me/badge?page_id=anzorq.finetuned_diffusion" alt="visitors"></p>
    </div>
    """)

    demo.load(update_state_info, inputs=state_info, outputs=state_info, every=0.5, show_progress=False)

print(f"Space built in {time.time() - start_time:.2f} seconds")

# if not is_colab:
demo.queue(concurrency_count=1)
demo.launch(debug=is_colab, share=is_colab)
