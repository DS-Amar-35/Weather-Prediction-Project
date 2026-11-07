# app.py
import streamlit as st
import os
from groq import Groq
from dotenv import load_dotenv
import sys

# Import MCP tools directly (Simple for beginners - No server needed)
sys.path.append(".")
from mcp_server import get_weather, search_docs, save_to_excel, generate_word_report, load_pdf_to_db

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

st.set_page_config(page_title="Smart AI Assistant", page_icon="🤖")
st.title("🤖 Smart Personal AI Assistant")
st.write("Groq LLM + RAG + MCP + ChromaDB + Weather + Excel + Word")

# Sidebar - Upload PDF
st.sidebar.header("📄 Upload Document for RAG")
uploaded = st.sidebar.file_uploader("Upload PDF", type=["pdf"])
if uploaded:
    os.makedirs("data", exist_ok=True)
    path = f"data/{uploaded.name}"
    with open(path, "wb") as f:
        f.write(uploaded.getbuffer())
    if st.sidebar.button("Load PDF to ChromaDB"):
        with st.spinner("Loading PDF..."):
            result = load_pdf_to_db(path)
            st.sidebar.success(result)

# Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat Input
prompt = st.chat_input("Ask: Weather in Hyderabad? / What is in PDF? / Save to Excel?")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Step 1: Let LLM decide which tool to use
            tool_prompt = f"""
            You are Smart Assistant. You have tools:
            - get_weather(city) for weather
            - search_docs(query) for PDF questions
            - save_to_excel(city, temperature) for Excel
            - generate_word_report(city, summary) for Word

            User question: {prompt}

            Reply in this format ONLY:
            TOOL: tool_name | PARAMS: value
            OR if no tool needed: TOOL: none

            Examples:
            User: Weather in Hyderabad? -> TOOL: get_weather | PARAMS: Hyderabad
            User: What is in my PDF about AI? -> TOOL: search_docs | PARAMS: AI
            User: Save Hyderabad weather to Excel -> TOOL: save_to_excel | PARAMS: Hyderabad, 28°C
            User: Generate report for Hyderabad -> TOOL: generate_word_report | PARAMS: Hyderabad, Weather is pleasant
            """

            decision = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "user", "content": tool_prompt}],
                temperature=0
            ).choices[0].message.content

            tool_result = ""
            # Step 2: Call the tool
            if "get_weather" in decision:
                city = decision.split("PARAMS:")[1].strip()
                tool_result = get_weather(city)
            elif "search_docs" in decision:
                q = decision.split("PARAMS:")[1].strip()
                tool_result = search_docs(q)
            elif "save_to_excel" in decision:
                parts = decision.split("PARAMS:")[1].strip().split(",")
                tool_result = save_to_excel(parts[0].strip(), parts[1].strip() if len(parts)>1 else "")
            elif "generate_word_report" in decision:
                parts = decision.split("PARAMS:")[1].strip().split(",")
                tool_result = generate_word_report(parts[0].strip(), parts[1].strip() if len(parts)>1 else prompt)
            else:
                tool_result = "No tool needed, answer directly."

            # Step 3: Final Answer from LLM using tool result
            final = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": "You are helpful assistant. Use tool result to answer. If tool result is from PDF, answer only from that."},
                    {"role": "user", "content": f"Question: {prompt}\nTool Result: {tool_result}\nGive final nice answer."}
                ],
                temperature=0.3
            ).choices[0].message.content

            st.write(final)
            st.session_state.messages.append({"role": "assistant", "content": final})

            # Show download buttons if files created
            if os.path.exists("outputs/weather_data.xlsx"):
                with open("outputs/weather_data.xlsx", "rb") as f:
                    st.download_button("📥 Download Excel", f, "weather_data.xlsx")
            if os.path.exists("outputs/report.docx"):
                with open("outputs/report.docx", "rb") as f:
                    st.download_button("📥 Download Word Report", f, "report.docx")