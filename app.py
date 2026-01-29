import streamlit as st
import os
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SerpAPIWrapper
from langchain.agents import AgentExecutor, create_react_agent
from datetime import datetime
from PIL import Image
import pytesseract

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="FactCheck AI - Trạm Xác Thực Sự Thật", page_icon="✅", layout="wide")

# Đường dẫn đến tesseract executable (Chỉ cần thiết nếu không có trong PATH)
# Nếu bạn cài đặt Tesseract và thêm vào PATH, có thể bỏ qua dòng này hoặc comment lại
# pytesseract.pytesseract.tesseract_cmd = r'/usr/local/bin/tesseract' # Ví dụ cho macOS, thay đổi cho Windows/Linux nếu cần

# --- LOGIC XỬ LÝ AI ---
def process_fact_check(claim, o_key, s_key):
    os.environ["OPENAI_API_KEY"] = o_key
    os.environ["SERPAPI_API_KEY"] = s_key
    
    # Check if keys are actually set
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("SERPAPI_API_KEY"):
        raise ValueError("API Keys are not set correctly in environment variables.")

    search = SerpAPIWrapper()
    tools = [
        Tool(
            name="Search_Official_News",
            func=search.run,
            description="Tìm kiếm tin tức từ báo chí chính thống và nguồn chính phủ."
        )
    ]
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0) # Sử dụng GPT-4o
    agent = initialize_agent(
        tools, llm, 
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
        verbose=True
    )
    
    prompt = f"""
    Bạn là một chuyên gia kiểm chứng tin tức. Hãy xác thực tin sau: "{claim}"
    Yêu cầu:
    1. Tìm các nguồn tin từ báo lớn (.vn, .gov, .org, .com uy tín).
    2. Trả về kết quả theo định dạng Markdown đẹp mắt:
       - **KẾT LUẬN**: [ĐÚNG/SAI/CẦN KIỂM CHỨNG]
       - **ĐỘ TIN CẬY**: [X%]
       - **PHÂN TÍCH**: (Tóm tắt ngắn gọn lý do)
       - **NGUỒN ĐỐI CHỨNG**: (Danh sách link)
    """
    return agent.run(prompt)

# --- GIAO DIỆN NGƯỜI DÙNG (UI) ---
st.markdown("<h1 style='text-align: center;'>🔍 FactCheck AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Hệ thống tự động xác thực tin tức dựa trên dữ liệu báo chí thời gian thực.</p>", unsafe_allow_html=True)
st.divider()

with st.sidebar:
    st.title("⚙️ Cấu hình hệ thống")
    openai_key = st.text_input("OpenAI API Key", type="password")
    serpapi_key = st.text_input("SerpAPI Key", type="password")
    st.info("Nhận key tại: [openai.com](https://platform.openai.com/api-keys) và [serpapi.com](https://serpapi.com/users/sign_up)")
    st.markdown("---")
    st.markdown("### Hướng dẫn:")
    st.markdown("1. Nhập API Keys.")
    st.markdown("2. Dán văn bản hoặc tải ảnh tin đồn lên.")
    st.markdown("3. Nhấn 'KIỂM CHỨNG NGAY'.")
    st.markdown("4. Đối với kiểm tra ảnh, hãy đảm bảo Tesseract OCR đã được cài đặt trên máy chủ (nếu tự host) hoặc Streamlit Cloud sẽ xử lý.")


# Tabs cho nhập văn bản hoặc tải ảnh
tab_text, tab_image = st.tabs(["💬 Kiểm chứng Văn bản/Link", "🖼️ Kiểm chứng Hình ảnh"])

processed_claim = ""

with tab_text:
    user_input_text = st.text_area("Dán đoạn tin đồn hoặc link báo cần kiểm chứng vào đây:", placeholder="Ví dụ: Việt Nam sắp ban hành luật mới về thuế tài sản...")
    if user_input_text:
        processed_claim = user_input_text

with tab_image:
    uploaded_file = st.file_uploader("Tải ảnh chụp màn hình hoặc hình ảnh tin đồn lên:", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Hình ảnh đã tải lên", use_column_width=True)
        try:
            image = Image.open(uploaded_file)
            st.info("Đang trích xuất văn bản từ hình ảnh...")
            extracted_text = pytesseract.image_to_string(image, lang='vie+eng') # Hỗ trợ tiếng Việt và tiếng Anh
            st.text_area("Văn bản trích xuất từ hình ảnh:", value=extracted_text, height=150, disabled=True)
            if extracted_text.strip():
                processed_claim = extracted_text
            else:
                st.warning("Không tìm thấy văn bản nào trong ảnh. Vui lòng thử lại với ảnh rõ ràng hơn.")
        except pytesseract.TesseractNotFoundError:
            st.error("Lỗi: Tesseract OCR engine không được tìm thấy. Vui lòng cài đặt Tesseract trên hệ thống của bạn (xem hướng dẫn ở sidebar).")
            st.stop()
        except Exception as e:
            st.error(f"Lỗi khi xử lý hình ảnh: {e}")
            st.stop()

col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    if st.button("🚀 KIỂM CHỨNG NGAY"):
        if not openai_key or not serpapi_key:
            st.error("Vui lòng nhập đầy đủ API Keys ở thanh bên trái!")
        elif not processed_claim:
            st.warning("Vui lòng nhập nội dung hoặc tải ảnh có văn bản để kiểm tra.")
        else:
            with st.spinner('AI đang quét các mặt báo và đối chiếu dữ liệu...'):
                try:
                    result = process_fact_check(processed_claim, openai_key, serpapi_key)
                    
                    st.success("Đã hoàn tất kiểm chứng!")
                    st.markdown("### 📊 Kết quả phân tích")
                    st.info(result)
                    
                    st.caption(f"Thời gian kiểm tra: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
                except Exception as e:
                    st.error(f"Có lỗi xảy ra: {str(e)}. Hãy đảm bảo API keys hợp lệ và nội dung đủ rõ ràng để AI phân tích.")

# --- CHÂN TRANG ---
st.divider()
st.markdown("<p style='text-align: center; color: gray;'>Sản phẩm được hỗ trợ bởi AI-driven Fact-checking Technology</p>", unsafe_allow_html=True)
