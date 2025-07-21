# app.py - Complete Streamlit application for cloud deployment with Claude Sonnet
import streamlit as st
import anthropic
import requests
import json
import os
from typing import List, Dict
import time
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import tempfile
import subprocess
import numpy as np
import zipfile

# Try to import MoviePy with fallback
try:
    from moviepy.editor import ImageSequenceClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, TextClip
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    MOVIEPY_AVAILABLE = False
    # Don't show error immediately, handle it gracefully later

# Configure page
st.set_page_config(
    page_title="AI Lesson Generator",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better appearance
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stProgress .st-bo {
        background-color: #00ff00;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 1rem 0;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .step-container {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'lesson_data' not in st.session_state:
    st.session_state.lesson_data = {}
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'generated_content' not in st.session_state:
    st.session_state.generated_content = None
if 'slides_approved' not in st.session_state:
    st.session_state.slides_approved = False

class LessonGenerator:
    def __init__(self, claude_key: str, elevenlabs_key: str):
        self.claude_key = claude_key
        self.elevenlabs_key = elevenlabs_key
        self.client = anthropic.Anthropic(api_key=claude_key)
        
    def extract_text_from_file(self, uploaded_file) -> str:
        """Extract text content from uploaded file"""
        try:
            if uploaded_file.type == "text/plain":
                return str(uploaded_file.read(), "utf-8")
            elif uploaded_file.type == "application/pdf":
                try:
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    return text
                except ImportError:
                    return "PDF support not available. Please use TXT files."
            elif uploaded_file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                try:
                    from docx import Document
                    doc = Document(uploaded_file)
                    text = ""
                    for paragraph in doc.paragraphs:
                        text += paragraph.text + "\n"
                    return text
                except ImportError:
                    return "DOCX support not available. Please use TXT files."
            else:
                return "Unsupported file type. Please use TXT files."
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def get_interesting_facts(self, topic: str, content: str) -> str:
        """Get interesting facts about the topic using Claude Sonnet"""
        try:
            prompt = f"""Based on the topic "{topic}" and the following content, find 5-7 interesting and engaging facts that would captivate students:

Content: {content[:2000]}

Focus on:
- Surprising statistics
- Historical anecdotes
- Real-world applications
- Fun trivia
- Current relevance

Format as a numbered list with brief explanations."""

            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=800,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            return f"Error generating facts: {str(e)}"
    
    def create_lesson_outline(self, objectives: str, content: str, facts: str) -> str:
        """Create a comprehensive lesson outline using Claude Sonnet"""
        try:
            prompt = f"""Create a detailed lesson outline based on:

Learning Objectives: {objectives}
Content Material: {content[:1500]}
Interesting Facts: {facts}

Structure the lesson with:
1. Introduction (5-10 minutes)
2. Main content sections (3-4 sections, 10-15 minutes each)
3. Interactive elements/activities
4. Conclusion and review (5-10 minutes)

Include timing estimates and key talking points for each section."""

            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1200,
                temperature=0.6,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            return f"Error creating outline: {str(e)}"
    
    def generate_slide_content(self, outline: str, objectives: str) -> List[Dict]:
        """Generate content for individual slides using Claude Sonnet"""
        try:
            prompt = f"""Based on this lesson outline and objectives, create content for 6 PowerPoint slides:

Outline: {outline}
Objectives: {objectives}

For each slide, provide:
1. Slide title
2. Key bullet points (3-4 points max)
3. Speaker notes (what the teacher should say)
4. Suggested image description for visual aid

Return ONLY valid JSON in this exact format:
[
    {{
        "slide_number": 1,
        "title": "Slide Title",
        "content": ["Point 1", "Point 2", "Point 3"],
        "speaker_notes": "Detailed explanation for this slide...",
        "image_description": "Description of suggested image"
    }}
]

Keep speaker notes concise but informative (2-3 sentences per slide)."""

            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1500,
                temperature=0.6,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse JSON response
            content = response.content[0].text.strip()
            # Remove any markdown formatting
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            slides_content = json.loads(content)
            return slides_content
        except Exception as e:
            st.error(f"Error generating slides: {str(e)}")
            # Return a basic slide structure as fallback
            return [
                {
                    "slide_number": 1,
                    "title": "Introduction",
                    "content": ["Welcome to the lesson", "Overview of objectives", "What we'll learn today"],
                    "speaker_notes": "Welcome students and introduce the lesson objectives. Set expectations for what they will learn.",
                    "image_description": "Welcoming classroom scene"
                }
            ]
    
    def generate_slide_images(self, image_descriptions: List[str]) -> List[str]:
        """Generate image prompts using Claude Sonnet for each slide"""
        try:
            enhanced_prompts = []
            for i, description in enumerate(image_descriptions):
                prompt = f"""Create a detailed, professional image prompt for an educational slide image based on this description: "{description}"

The prompt should be:
- Suitable for educational content
- Professional and clean
- Engaging for students
- Appropriate for classroom use

Return only the enhanced image prompt, nothing else."""

                response = self.client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=200,
                    temperature=0.7,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                enhanced_prompts.append(response.content[0].text.strip())
            
            return enhanced_prompts
        except Exception as e:
            st.warning(f"Error enhancing image descriptions: {str(e)}")
            return image_descriptions
        """Create PowerPoint presentation"""
        try:
            prs = Presentation()
            
            # Title slide
            title_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(title_layout)
            title = slide.shapes.title
            subtitle = slide.placeholders[1]
            
            title.text = lesson_title
            subtitle.text = "AI-Generated Educational Content"
            
            # Content slides
            for slide_data in slides_data:
                bullet_layout = prs.slide_layouts[1]
                slide = prs.slides.add_slide(bullet_layout)
                
                title_shape = slide.shapes.title
                title_shape.text = slide_data['title']
                
                content_shape = slide.placeholders[1]
                text_frame = content_shape.text_frame
                text_frame.clear()
                
                for point in slide_data['content']:
                    p = text_frame.add_paragraph()
                    p.text = point
                    p.level = 0
            
            # Save to BytesIO
            pptx_buffer = io.BytesIO()
            prs.save(pptx_buffer)
            pptx_buffer.seek(0)
            
            return pptx_buffer
        except Exception as e:
            st.error(f"Error creating PowerPoint: {str(e)}")
            return None
    
    def generate_audio(self, text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> bytes:
        """Generate audio using ElevenLabs API"""
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                return response.content
            else:
                st.error(f"ElevenLabs API error: {response.status_code}")
                return None
        except Exception as e:
            st.error(f"Error generating audio: {str(e)}")
            return None
    
    def create_video(self, slides_data: List[Dict], audio_files: List[tuple], lesson_title: str, output_path: str) -> str:
        """Create video from slides and audio using MoviePy"""
        if not MOVIEPY_AVAILABLE:
            st.warning("⚠️ Video generation is not available in this environment.")
            st.info("💡 You can still download PowerPoint and audio files and combine them manually using video editing software.")
            return None
            
        try:
            # Import MoviePy functions here to avoid module-level import issues
            from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_videoclips
            
            with tempfile.TemporaryDirectory() as temp_dir:
                st.info("🎬 Creating video presentation...")
                
                # Create slide images
                image_paths = []
                for i, slide_data in enumerate(slides_data):
                    # Create slide image
                    img_width, img_height = 1280, 720
                    img = Image.new('RGB', (img_width, img_height), 'white')
                    draw = ImageDraw.Draw(img)
                    
                    # Use basic fonts (most reliable across platforms)
                    try:
                        # Try to use better fonts if available
                        title_font = ImageFont.truetype("arial.ttf", 48)
                        content_font = ImageFont.truetype("arial.ttf", 32)
                    except:
                        try:
                            # Fallback fonts for different systems
                            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 48)
                            content_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 32)
                        except:
                            # Final fallback
                            title_font = ImageFont.load_default()
                            content_font = ImageFont.load_default()
                    
                    # Draw title
                    title = slide_data['title']
                    try:
                        bbox = draw.textbbox((0, 0), title, font=title_font)
                        title_width = bbox[2] - bbox[0]
                    except:
                        title_width = len(title) * 30  # Rough estimate
                    
                    title_x = max(50, (img_width - title_width) // 2)
                    draw.text((title_x, 80), title, fill='black', font=title_font)
                    
                    # Draw content points
                    y_offset = 200
                    for point in slide_data['content']:
                        # Simple text wrapping
                        words = point.split()
                        lines = []
                        current_line = []
                        
                        for word in words:
                            test_line = ' '.join(current_line + [word])
                            try:
                                bbox = draw.textbbox((0, 0), test_line, font=content_font)
                                test_width = bbox[2] - bbox[0]
                            except:
                                test_width = len(test_line) * 20  # Rough estimate
                            
                            if test_width < img_width - 150:
                                current_line.append(word)
                            else:
                                if current_line:
                                    lines.append(' '.join(current_line))
                                current_line = [word]
                        
                        if current_line:
                            lines.append(' '.join(current_line))
                        
                        for line in lines:
                            draw.text((75, y_offset), f"• {line}", fill='black', font=content_font)
                            y_offset += 40
                        
                        y_offset += 15
                    
                    # Save image
                    img_path = os.path.join(temp_dir, f"slide_{i:03d}.png")
                    img.save(img_path)
                    image_paths.append(img_path)
                
                # Save audio files
                audio_paths = []
                for i, (filename, audio_content) in enumerate(audio_files):
                    audio_path = os.path.join(temp_dir, f"audio_{i:03d}.mp3")
                    with open(audio_path, 'wb') as f:
                        f.write(audio_content)
                    audio_paths.append(audio_path)
                
                # Create video clips
                video_clips = []
                
                for i, (img_path, audio_path) in enumerate(zip(image_paths, audio_paths)):
                    try:
                        # Load audio to get duration
                        audio_clip = AudioFileClip(audio_path)
                        duration = max(4.0, audio_clip.duration)
                        
                        # Create image clip
                        img_clip = (ImageSequenceClip([img_path], fps=1)
                                   .set_duration(duration)
                                   .resize((1280, 720)))
                        
                        # Combine image and audio
                        video_clip = img_clip.set_audio(audio_clip)
                        video_clips.append(video_clip)
                        
                        audio_clip.close()
                    except Exception as e:
                        st.warning(f"Issue with slide {i+1}: {str(e)}")
                        continue
                
                if not video_clips:
                    st.error("No video clips were created successfully")
                    return None
                
                # Concatenate clips
                final_video = concatenate_videoclips(video_clips)
                
                # Write video with cloud-optimized settings
                final_video.write_videofile(
                    output_path,
                    fps=24,
                    codec='libx264',
                    audio_codec='aac',
                    verbose=False,
                    logger=None,
                    preset='ultrafast'
                )
                
                # Clean up
                final_video.close()
                for clip in video_clips:
                    clip.close()
                
                return output_path
                
        except ImportError:
            st.warning("⚠️ MoviePy is not properly installed for video generation.")
            st.info("💡 PowerPoint and audio files are still available for download.")
            return None
        except Exception as e:
            st.error(f"Error creating video: {str(e)}")
            return None

def main():
    # Header
    st.title("🎓 AI-Powered Lesson Generator")
    st.markdown("### Transform your teaching materials into engaging multimedia lessons")
    
    # Display deployment info
    st.markdown("""
    <div class="info-box">
        🌐 <strong>Deployed on Streamlit Cloud</strong> - Professional lesson generation powered by Claude Sonnet AI<br>
        📄 Generate PowerPoint presentations and audio narration instantly!
    </div>
    """, unsafe_allow_html=True)
    
    # Show MoviePy status
    if not MOVIEPY_AVAILABLE:
        st.markdown("""
        <div style="padding: 0.5rem; border-radius: 0.5rem; background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; margin: 1rem 0;">
            ⚠️ <strong>Note:</strong> Video generation is not available in this environment. You'll still get PowerPoint slides and audio files!
        </div>
        """, unsafe_allow_html=True)
    
    # Sidebar for API keys and settings
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Keys section
        with st.expander("🔐 API Keys", expanded=True):
            claude_key = st.text_input(
                "Anthropic Claude API Key", 
                type="password", 
                help="Get from: https://console.anthropic.com/"
            )
            elevenlabs_key = st.text_input(
                "ElevenLabs API Key", 
                type="password", 
                help="Get from: https://elevenlabs.io/"
            )
        
        if not claude_key or not elevenlabs_key:
            st.warning("⚠️ Please enter both API keys to continue")
            with st.expander("📝 How to get API keys"):
                st.markdown("""
                **Anthropic Claude API Key:**
                1. Go to [Anthropic Console](https://console.anthropic.com/)
                2. Sign up or log in
                3. Navigate to API Keys section
                4. Create a new API key
                5. Copy and paste it above
                
                **ElevenLabs API Key:**
                1. Go to [ElevenLabs](https://elevenlabs.io/)
                2. Sign up for free account
                3. Go to your profile settings
                4. Copy your API key
                """)
            return
        
        # Progress tracking
        st.header("📊 Progress")
        progress_steps = [
            "Input & Upload",
            "Content Analysis", 
            "Review & Approve",
            "Generate Materials",
            "Final Output"
        ]
        
        for i, step in enumerate(progress_steps, 1):
            if i < st.session_state.current_step:
                st.success(f"✅ {step}")
            elif i == st.session_state.current_step:
                st.info(f"🔄 {step}")
            else:
                st.write(f"⏳ {step}")
        
        # About section
        with st.expander("ℹ️ About"):
            st.markdown("""
            This app generates complete lesson materials including:
            - 📄 PowerPoint presentations
            - 🎵 Audio narration
            - 🎬 Complete video lessons
            
            Built with ❤️ using Streamlit, Claude Sonnet, and ElevenLabs.
            """)
    
    # Initialize lesson generator
    if claude_key and elevenlabs_key:
        lesson_gen = LessonGenerator(claude_key, elevenlabs_key)
    else:
        return
    
    # Main content area
    main_container = st.container()
    
    with main_container:
        # Step 1: Input Collection
        if st.session_state.current_step == 1:
            st.markdown('<div class="step-container">', unsafe_allow_html=True)
            st.header("📝 Step 1: Lesson Setup")
            
            col1, col2 = st.columns(2)
            
            with col1:
                lesson_title = st.text_input(
                    "Lesson Title", 
                    placeholder="e.g., Introduction to Photosynthesis"
                )
                subject = st.selectbox(
                    "Subject", 
                    ["Science", "Math", "History", "English", "Social Studies", "Other"]
                )
                grade_level = st.selectbox(
                    "Grade Level", 
                    ["Elementary", "Middle School", "High School", "College"]
                )
            
            with col2:
                duration = st.slider("Lesson Duration (minutes)", 10, 60, 30)
                objectives = st.text_area(
                    "Learning Objectives", 
                    placeholder="What should students learn by the end of this lesson?",
                    height=150
                )
            
            st.subheader("📎 Upload Learning Material")
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=['txt'],
                help="Upload your lesson content, notes, or reference material (TXT format recommended for cloud deployment)"
            )
            
            # Quick demo option
            demo_section = st.expander("🚀 Quick Demo (No upload required)")
            with demo_section:
                st.info("Try the app instantly with pre-loaded content!")
                
                if st.checkbox("Use Demo Content: Renewable Energy Lesson"):
                    lesson_title = "Introduction to Renewable Energy"
                    objectives = "Students will understand different types of renewable energy sources and their benefits for the environment."
                    demo_content = """
                    Renewable energy comes from natural resources that are constantly replenished, such as sunlight, wind, rain, tides, waves, and geothermal heat. Unlike fossil fuels, renewable energy sources produce little to no greenhouse gases or pollutants.

                    Types of Renewable Energy:
                    1. Solar Energy - Captured using solar panels that convert sunlight into electricity through photovoltaic cells
                    2. Wind Energy - Generated by wind turbines that harness kinetic energy from moving air
                    3. Hydroelectric Power - Uses flowing or falling water to spin turbines and generate electricity
                    4. Geothermal Energy - Harnesses heat from the Earth's core for heating and electricity generation
                    5. Biomass - Uses organic materials like wood, agricultural waste, and algae for fuel

                    Benefits include reduced carbon emissions, energy independence, job creation in green industries, and sustainable development for future generations. The renewable energy sector has grown rapidly, with costs dropping significantly over the past decade.
                    """
                    
                    if st.button("🎯 Generate Demo Lesson", type="primary"):
                        with st.spinner("Creating demo lesson..."):
                            facts = lesson_gen.get_interesting_facts(lesson_title, demo_content)
                            
                            st.session_state.lesson_data = {
                                'title': lesson_title,
                                'subject': 'Science',
                                'grade_level': 'High School',
                                'duration': 30,
                                'objectives': objectives,
                                'content': demo_content,
                                'facts': facts
                            }
                            st.session_state.current_step = 2
                            st.rerun()
            
            # Process uploaded file
            if uploaded_file and lesson_title and objectives:
                if st.button("🚀 Analyze Content & Generate Facts", type="primary"):
                    with st.spinner("Processing your content..."):
                        content = lesson_gen.extract_text_from_file(uploaded_file)
                        facts = lesson_gen.get_interesting_facts(lesson_title, content)
                        
                        st.session_state.lesson_data = {
                            'title': lesson_title,
                            'subject': subject,
                            'grade_level': grade_level,
                            'duration': duration,
                            'objectives': objectives,
                            'content': content,
                            'facts': facts
                        }
                        st.session_state.current_step = 2
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Step 2: Content Analysis and Review
        elif st.session_state.current_step == 2:
            st.markdown('<div class="step-container">', unsafe_allow_html=True)
            st.header("🔍 Step 2: Content Analysis & Review")
            
            data = st.session_state.lesson_data
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📚 Extracted Content Preview")
                st.text_area("Content", data['content'][:500] + "...", height=200, disabled=True)
                
            with col2:
                st.subheader("🎯 Interesting Facts Generated")
                st.markdown(data['facts'])
            
            st.subheader("📋 Lesson Overview")
            with st.expander("Review Lesson Details", expanded=True):
                st.write(f"**Title:** {data['title']}")
                st.write(f"**Subject:** {data['subject']}")
                st.write(f"**Grade Level:** {data['grade_level']}")
                st.write(f"**Duration:** {data['duration']} minutes")
                st.write(f"**Objectives:** {data['objectives']}")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("⬅️ Back to Edit", type="secondary"):
                    st.session_state.current_step = 1
                    st.rerun()
            
            with col2:
                if st.button("🔄 Regenerate Facts", type="secondary"):
                    with st.spinner("Regenerating facts..."):
                        new_facts = lesson_gen.get_interesting_facts(data['title'], data['content'])
                        st.session_state.lesson_data['facts'] = new_facts
                        st.rerun()
            
            with col3:
                if st.button("✅ Create Lesson Outline", type="primary"):
                    with st.spinner("Creating lesson outline and slide content..."):
                        outline = lesson_gen.create_lesson_outline(
                            data['objectives'], data['content'], data['facts']
                        )
                        slides = lesson_gen.generate_slide_content(outline, data['objectives'])
                        
                        st.session_state.lesson_data['outline'] = outline
                        st.session_state.lesson_data['slides'] = slides
                        st.session_state.current_step = 3
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Step 3: Review and Approve
        elif st.session_state.current_step == 3:
            st.markdown('<div class="step-container">', unsafe_allow_html=True)
            st.header("👀 Step 3: Review & Approve Content")
            
            data = st.session_state.lesson_data
            
            st.subheader("📋 Lesson Outline")
            with st.expander("View Complete Outline", expanded=True):
                st.markdown(data['outline'])
            
            st.subheader("🖼️ Slide Previews")
            
            if 'slides' in data and data['slides']:
                for slide in data['slides']:
                    with st.expander(f"Slide {slide['slide_number']}: {slide['title']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Content:**")
                            for point in slide['content']:
                                st.write(f"• {point}")
                            st.write(f"**Suggested Image:** {slide['image_description']}")
                        
                        with col2:
                            st.write("**Speaker Notes:**")
                            st.write(slide['speaker_notes'])
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("⬅️ Back to Analysis", type="secondary"):
                    st.session_state.current_step = 2
                    st.rerun()
            
            with col2:
                if st.button("🔄 Regenerate Slides", type="secondary"):
                    with st.spinner("Regenerating slide content..."):
                        new_slides = lesson_gen.generate_slide_content(
                            data['outline'], data['objectives']
                        )
                        st.session_state.lesson_data['slides'] = new_slides
                        st.rerun()
            
            with col3:
                if st.button("✅ Approve & Generate Materials", type="primary"):
                    st.session_state.slides_approved = True
                    st.session_state.current_step = 4
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Step 4: Generate Materials
        elif st.session_state.current_step == 4:
            st.markdown('<div class="step-container">', unsafe_allow_html=True)
            st.header("🎬 Step 4: Generate Presentation Materials")
            
            data = st.session_state.lesson_data
            
            if not st.session_state.slides_approved:
                st.error("Please approve the content first")
                return
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Generate PowerPoint
            status_text.text("Creating PowerPoint presentation...")
            progress_bar.progress(20)
            
            pptx_buffer = lesson_gen.create_powerpoint(data['slides'], data['title'])
            
            if pptx_buffer:
                # Generate audio for each slide
                status_text.text("Generating audio narration...")
                progress_bar.progress(40)
                
                audio_files = []
                for i, slide in enumerate(data['slides']):
                    status_text.text(f"Generating audio for slide {i+1}...")
                    audio_content = lesson_gen.generate_audio(slide['speaker_notes'])
                    if audio_content:
                        audio_files.append((f"slide_{i+1}.mp3", audio_content))
                    
                    progress_bar.progress(40 + (i+1) * 30 / len(data['slides']))
                
                # Generate video (if MoviePy is available)
                if MOVIEPY_AVAILABLE:
                    status_text.text("Creating final video presentation...")
                    progress_bar.progress(80)
                    
                    video_path = os.path.join(tempfile.gettempdir(), f"{data['title']}_lesson.mp4")
                    final_video_path = lesson_gen.create_video(data['slides'], audio_files, data['title'], video_path)
                else:
                    final_video_path = None
                    st.warning("⚠️ Video generation is not available in this environment. PowerPoint and audio files will still be generated.")
                
                progress_bar.progress(100)
                status_text.text("✅ Generation complete!")
                
                st.session_state.pptx_buffer = pptx_buffer
                st.session_state.audio_files = audio_files
                st.session_state.video_path = final_video_path
                st.session_state.current_step = 5
                
                time.sleep(2)
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Step 5: Final Output
        elif st.session_state.current_step == 5:
            st.markdown('<div class="step-container">', unsafe_allow_html=True)
            st.header("🎉 Step 5: Download Your Materials")
            
            st.markdown("""
            <div class="success-box">
                ✅ Your lesson materials have been generated successfully!
            </div>
            """, unsafe_allow_html=True)
            
            data = st.session_state.lesson_data
            
            # Summary
            with st.expander("📊 Lesson Summary", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Title", data['title'])
                    st.metric("Subject", data['subject'])
                    st.metric("Grade Level", data['grade_level'])
                with col2:
                    st.metric("Slides Generated", len(data['slides']))
                    st.metric("Audio Files", len(st.session_state.audio_files))
                    st.metric("Duration", f"{data['duration']} minutes")
            
            # Download section
            st.subheader("📥 Download Your Materials")
            
            # Main download buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if hasattr(st.session_state, 'pptx_buffer'):
                    st.download_button(
                        label="📄 Download PowerPoint",
                        data=st.session_state.pptx_buffer.getvalue(),
                        file_name=f"{data['title']}.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        help="Editable PowerPoint presentation"
                    )
            
            with col2:
                if hasattr(st.session_state, 'video_path') and st.session_state.video_path:
                    if os.path.exists(st.session_state.video_path):
                        with open(st.session_state.video_path, 'rb') as video_file:
                            st.download_button(
                                label="🎬 Download Video",
                                data=video_file.read(),
                                file_name=f"{data['title']}_lesson.mp4",
                                mime="video/mp4",
                                help="Complete lesson video with narration"
                            )
            
            with col3:
                if hasattr(st.session_state, 'audio_files') and st.session_state.audio_files:
                    # Create ZIP file with all audio files
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for filename, audio_content in st.session_state.audio_files:
                            zip_file.writestr(filename, audio_content)
                    
                    zip_buffer.seek(0)
                    
                    st.download_button(
                        label="🔊 Download Audio Files",
                        data=zip_buffer.getvalue(),
                        file_name=f"{data['title']}_audio.zip",
                        mime="application/zip",
                        help="All narration audio files in ZIP format"
                    )
            
            # Individual audio files section
            if hasattr(st.session_state, 'audio_files') and st.session_state.audio_files:
                with st.expander("🎵 Individual Audio Files"):
                    st.write("Download individual slide narrations:")
                    cols = st.columns(3)
                    for i, (filename, audio_content) in enumerate(st.session_state.audio_files):
                        col_idx = i % 3
                        with cols[col_idx]:
                            st.download_button(
                                label=f"🔊 {filename}",
                                data=audio_content,
                                file_name=filename,
                                mime="audio/mpeg",
                                key=f"audio_{i}"
                            )
            
            # Status messages
            if hasattr(st.session_state, 'video_path') and st.session_state.video_path:
                st.success("🎉 Complete lesson video has been generated successfully!")
                st.info(f"📹 Video specs: {data['duration']} minutes | 1280x720 HD | MP4 format")
            else:
                st.warning("⚠️ Video generation had issues. PowerPoint and audio files are still available.")
            
            # Action buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Create Another Lesson", type="primary"):
                    # Reset session state
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
            
            with col2:
                if st.button("📧 Share Feedback", type="secondary"):
                    st.info("💌 Love the app? Have suggestions? Let us know!")
            
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
