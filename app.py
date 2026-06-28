import streamlit as st
import os
import json
import srt
from openai import OpenAI
from elevenlabs import generate, save, set_api_key
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx

# App ခေါင်းစဉ်
st.set_page_config(page_title="AI Movie Shorts Creator", layout="wide")
st.title("🎬 AI Movie Shorts Creator")
st.write("ရုပ်ရှင်ဗီဒီယိုရှည်များကို AI အသုံးပြု၍ Recap ဗီဒီယိုတိုများအဖြစ် ပြောင်းလဲပေးသည့် App")

# Sidebar - API Keys သတ်မှတ်ရန်
st.sidebar.header("🔑 API Configurations")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
elevenlabs_key = st.sidebar.text_input("ElevenLabs API Key", type="password")
selected_voice = st.sidebar.selectbox("ElevenLabs Voice ID", ["Rachel", "Drew", "Clyde"])

# ဖိုင်တင်ရန် နေရာများ
col1, col2 = st.columns(2)
with col1:
    uploaded_video = st.file_uploader("ရုပ်ရှင်ဗီဒီယို တင်ပါ (.mp4)", type=["mp4"])
with col2:
    uploaded_srt = st.file_uploader("စာတန်းထိုးဖိုင် တင်ပါ (.srt)", type=["srt"])

def parse_srt(srt_file_path):
    """SRT ဖိုင်မှ စာသားများကို ဖတ်ရှုပြီး စက္ကန့်အလိုက် ပြောင်းလဲပေးသည့် function"""
    with open(srt_file_path, 'r', encoding='utf-8') as f:
        subs = list(srt.parse(f.read()))
    sub_list = []
    for sub in subs:
        sub_list.append({
            "start": sub.start.total_seconds(),
            "end": sub.end.total_seconds(),
            "text": sub.content
        })
    return sub_list

def generate_clip_plan(openai_client, subtitles):
    """OpenAI သို့ စာတန်းထိုးများပေးပို့ပြီး ဖြတ်တောက်ရမည့် အချိန်နှင့် ပြောရမည့် script ယူခြင်း"""
    prompt = f"""
    You are a professional movie recap creator. 
    Here are the subtitles of a movie with timestamps:
    {json.dumps(subtitles[:100])} # Limits tokens for demo purposes
    
    Choose exactly 3 to 5 most important scenes to create an engaging movie recap.
    For each scene, specify:
    1. The start and end timestamps (in seconds).
    2. A brief, exciting recap narration script (around 15-20 words).
    
    Format the response STRICTLY as a JSON list like this:
    [
      {{"start": 10.0, "end": 25.0, "narration": "We meet our protagonist as he makes a shocking discovery in his backyard."}},
      {{"start": 120.0, "end": 135.0, "narration": "Soon, the threat intensifies and he has to run for his life."}}
    ]
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"} if "mini" in "gpt-4o-mini" else None
    )
    
    return json.loads(response.choices[0].message.content)

# စတင်လုပ်ဆောင်ရန် ခလုတ်
if st.button("🚀 ဗီဒီယို စတင်ဖန်တီးပါ") and uploaded_video and uploaded_srt:
    if not openai_key or not elevenlabs_key:
        st.error("ကျေးဇူးပြု၍ OpenAI နှင့် ElevenLabs API Key များကို ထည့်သွင်းပေးပါ။")
    else:
        # ယာယီ ဖိုဒါများ ဆောက်ခြင်း
        os.makedirs("temp", exist_ok=True)
        os.makedirs("output", exist_ok=True)
        
        # ဖိုင်များကို သိမ်းဆည်းခြင်း
        video_path = os.path.join("temp", "input_movie.mp4")
        srt_path = os.path.join("temp", "subtitles.srt")
        
        with open(video_path, "wb") as f:
            f.write(uploaded_video.getbuffer())
        with open(srt_path, "wb") as f:
            f.write(uploaded_srt.getbuffer())
            
        st.info("⏳ အဆင့် ၁: စာတန်းထိုးများကို ပိုင်းခြားစိတ်ဖြာနေပါသည်...")
        subtitles = parse_srt(srt_path)
        
        st.info("⏳ အဆင့် ၂: OpenAI အသုံးပြု၍ ဇာတ်လမ်းအကျဉ်းချုပ်နှင့် Clip Plan ရေးဆွဲနေပါသည်...")
        openai_client = OpenAI(api_key=openai_key)
        clip_plan_data = generate_clip_plan(openai_client, subtitles)
        
        # API Response ကို စစ်ဆေးခြင်း
        if "clips" in clip_plan_data:
            clips_list = clip_plan_data["clips"]
        elif isinstance(clip_plan_data, list):
            clips_list = clip_plan_data
        else:
            clips_list = list(clip_plan_data.values())[0]
            
        st.write("🎯 AI မှ စီစဉ်ပေးလိုက်သည့် အစီအစဉ် -")
        st.json(clips_list)
        
        # ElevenLabs Setup
        set_api_key(elevenlabs_key)
        
        processed_clips = []
        original_video = VideoFileClip(video_path)
        
        st.info("⏳ အဆင့် ၃: ဗီဒီယိုများကို ဖြတ်တောက်ပြီး AI အသံနောက်ခံများ ထည့်သွင်းနေပါသည်...")
        
        for idx, item in enumerate(clips_list):
            st.write(f"🔊 အပိုင်း ({idx+1}) အတွက် အသံနှင့် ဗီဒီယိုကို စီစဉ်နေသည်...")
            start_t = item["start"]
            end_t = item["end"]
            narration_text = item["narration"]
            
            # AI အသံဖန်တီးခြင်း
            audio_bytes = generate(
                text=narration_text,
                voice=selected_voice,
                model="eleven_monolingual_v1"
            )
            audio_temp_path = f"temp/audio_{idx}.mp3"
            save(audio_bytes, audio_temp_path)
            
            # ဗီဒီယိုဖြတ်တောက်ခြင်း
            sub_clip = original_video.subclip(start_t, end_t)
            narration_audio = AudioFileClip(audio_temp_path)
            
            # ဗီဒီယိုနှင့် အသံ အရှည်ကို ညီအောင် အမြန်နှုန်းညှိခြင်း (Speed Stretching)
            duration_ratio = sub_clip.duration / narration_audio.duration
            stretched_clip = sub_clip.fx(vfx.speedx, duration_ratio)
            
            # အသံနောက်ခံ ထည့်သွင်းခြင်း
            final_sub_clip = stretched_clip.set_audio(narration_audio)
            processed_clips.append(final_sub_clip)
            
        # ဗီဒီယိုများအားလုံးကို တစ်ခုတည်းဖြစ်အောင် ပြန်ပေါင်းခြင်း
        st.info("⏳ အဆင့် ၄: ဗီဒီယိုအကျဉ်းချုပ်ကို ပေါင်းစပ်ထုတ်လုပ်နေပါသည်...")
        final_recap_video = concatenate_videoclips(processed_clips)
        
        # 16:9 ပုံမှန်ဗီဒီယို ထုတ်ခြင်း
        output_horizontal_path = "output/recap_horizontal.mp4"
        final_recap_video.write_videofile(output_horizontal_path, codec="libx264", audio_codec="aac")
        
        # TikTok အတွက် 9:16 ဒေါင်လိုက်ဗီဒီယိုသို့ ပြောင်းလဲခြင်း
        st.info("⏳ အဆင့် ၅: TikTok/Shorts အတွက် ဒေါင်လိုက် (9:16) ဗီဒီယို ပြောင်းလဲနေပါသည်...")
        w, h = final_recap_video.size
        # အလယ်တည့်တည့်မှ 9:16 အတိုင်း ဖြတ်ယူခြင်း
        target_width = int(h * 9 / 16)
        x_center = w / 2
        vertical_video = final_recap_video.crop(x1=x_center - target_width/2, y1=0, x2=x_center + target_width/2, y2=h)
        
        output_vertical_path = "output/recap_vertical.mp4"
        vertical_video.write_videofile(output_vertical_path, codec="libx264", audio_codec="aac")
        
        st.success("🎉 ဗီဒီယိုများ အောင်မြင်စွာ ဖန်တီးပြီးပါပြီ။")
        
        # ရလဒ်များကို ပြသခြင်းနှင့် ဒေါင်းလုဒ်လုပ်ခွင့်ပေးခြင်း
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.subheader("Widescreen Recap (16:9)")
            st.video(output_horizontal_path)
            with open(output_horizontal_path, "rb") as file:
                st.download_button(label="Horizontal Video ဒေါင်းလုဒ်ဆွဲရန်", data=file, file_name="recap_horizontal.mp4")
                
        with col_res2:
            st.subheader("TikTok/Shorts Recap (9:16)")
            st.video(output_vertical_path)
            with open(output_vertical_path, "rb") as file:
                st.download_button(label="Vertical Video ဒေါင်းလုဒ်ဆွဲရန်", data=file, file_name="recap_vertical.mp4")
                
        # ယာယီဖိုင်များ ရှင်းလင်းခြင်း
        original_video.close()
        for clip in processed_clips:
            clip.close()
