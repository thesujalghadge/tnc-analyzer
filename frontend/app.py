import streamlit as st
import requests

API_ANALYZE = "http://127.0.0.1:8000/analyze"
API_ASK = "http://127.0.0.1:8000/ask"

st.title("📄 AI Terms & Conditions Analyzer")

# -------------------------------
# SESSION STATE (important)
# -------------------------------
if "document_loaded" not in st.session_state:
    st.session_state.document_loaded = False

if "document_id" not in st.session_state:
    st.session_state.document_id = None


# -------------------------------
# FILE UPLOAD
# -------------------------------
uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file is not None:

    st.info("Uploading and analyzing document...")

    files = {
        "file": (uploaded_file.name, uploaded_file, "application/pdf")
    }

    try:
        response = requests.post(API_ANALYZE, files=files)

        if response.status_code == 200:
            payload = response.json()
            result = payload["formatted_output"]

            st.success("Analysis Complete ✅")
            st.text_area("Result", result, height=500)

            # ✅ mark as ready for Q&A
            st.session_state.document_loaded = True
            st.session_state.document_id = payload["document_id"]

        else:
            st.error(f"API Error: {response.status_code}")

    except Exception as e:
        st.error(f"Connection Error: {e}")


# -------------------------------
# Q&A SECTION
# -------------------------------
st.subheader("💬 Chat with Document")

if not st.session_state.document_loaded:
    st.warning("⚠️ Please upload and analyze a document first.")
else:
    question = st.text_input("Ask something about the document")

    if st.button("Ask"):
        if not question.strip():
            st.warning("Please enter a question")
        else:
            with st.spinner("Thinking... 🤖"):
                try:
                    response = requests.post(
                        API_ASK,
                        json={
                            "question": question,
                            "document_id": st.session_state.document_id,
                        }
                    )

                    result = response.json()

                    if "detail" in result:
                        st.error(result["detail"])
                    else:
                        st.write("### 🧠 Answer:")
                        st.write(result["answer"])

                        status_label = "Grounded" if result["grounded"] else "Low support"
                        st.caption(f"{status_label} | Confidence: {result['confidence']:.2f}")

                        st.write("### 📌 Citations:")

                        for ev in result["citations"]:
                            st.info(
                                f"Page {ev['page_number']} | Chunk {ev['chunk_id'] + 1} | "
                                f"Relevance {ev['relevance_score']:.2f}\n\n{ev['text'][:300]}"
                            )

                except Exception as e:
                    st.error(f"Connection Error: {e}")
