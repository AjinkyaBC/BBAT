import time
import streamlit as st
import fitz
import pandas as pd
import openai
import re
import streamlit.components.v1 as components
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv()  # read local .env file
dotenv_path = os.path.join(".env")

print(dotenv_path)
openai.api_key=os.getenv("OPENAI_API_KEY1")

openai.api_base = "https://bc-api-management-uksouth.azure-api.net"
openai.api_type = 'azure'
openai.api_version = "2023-03-15-preview"
openai.log = "debug"


# Function to extract text from uploaded PDF files
def extract_text_from_pdf(file):
    pdf_doc = fitz.open(stream=file.read(), filetype="pdf")
    extracted_text = ""
    for page in pdf_doc:
        extracted_text += page.get_text("text")
    return extracted_text


def yes_no_unsure(text):
    response = openai.ChatCompletion.create(
        engine="gpt-4-32k",
        messages=[{"role": "system", "content": text}],
        temperature=0.07,
        max_tokens=1200,
        top_p=1
    )
    time.sleep(2)
    return response['choices'][0]['message']['content']


def score_different(txt, resp, df):
    filt_df = df[df['Questions'] == txt]
    
    if txt == 'How does the applicant describe the way they walk?':
        pat1 = 'normal'
        pat2 = 'adequate'
        pat3 = 'poor'
        pat4 = 'very poor'
        pat5 = 'other'
        if re.search(pat1, resp.lower()) is not None:
            return filt_df['Yes'].values[0]
        elif re.search(pat2, resp.lower()) is not None:
            return filt_df['No'].values[0]
        elif re.search(pat3, resp.lower()) is not None:
            return filt_df['Unsure'].values[0]
        elif re.search(pat4, resp.lower()) is not None:
            return filt_df['A'].values[0]
        elif re.search(pat5, resp.lower()) is not None:
            return filt_df['B'].values[0]
    elif txt == 'How far is the applicant able to walk? ':
        pat1 = '<30 m'
        pat2 = '<80 m'
        pat3 = '>80 m'
        if re.search(pat1, resp) is not None:
            return filt_df['Yes'].values[0]
        elif re.search(pat2, resp) is not None:
            return filt_df['No'].values[0]
        elif re.search(pat3, resp) is not None:
            return filt_df['Unsure'].values[0]
    elif txt == 'How long can you walk for, using a mobility aid, without stopping':
        pat1 = 'Can\'t walk'
        pat2 = '<1 min'
        pat3 = '1-5 mins'
        pat4 = '5-10 mins'
        pat5 = '>10 mins'
        if re.search(pat1, resp) is not None:
            return filt_df['Yes'].values[0]
        elif re.search(pat2, resp) is not None:
            return filt_df['No'].values[0]
        elif re.search(pat3, resp) is not None:
            return filt_df['Unsure'].values[0]
        elif re.search(pat4, resp) is not None:
            return filt_df['A'].values[0]
        elif re.search(pat5, resp) is not None:
            return filt_df['B'].values[0]

def display_success_icon():
    components.html(
        """
        <div style="text-align:center">
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24">
                <path d="M0 0h24v24H0z" fill="none"/>
                <path fill="#2196f3" d="M20.59 6.58L9 18.17l-5.59-5.59L2 14l7 7 12-12z"/>
            </svg>
            <p style="font-size: 20px; color: #2196f3; font-weight: bold;">Issue Blue Badge</p>
        </div>
        """
    )

def generate_reasons_for_rejection(sections, threshold):
    reasons = []
    for index, row in sections.iterrows():
        question = row['Question']
        answer = row['Answer']
        score = row['Score']
        if score <= threshold:
            reason = f"The answer to the question '{question}' received a score of {score}, which indicates a potential issue. Here's the answer provided: \n\n'{answer}'"
            reasons.append(reason)
    return reasons


def score(txt, resp, df):
    filt_df = df[df['Questions'] == txt]
    pat1 = 'Yes'
    pat2 = 'No'
    if re.search(pat1, resp) is not None:
        return filt_df['Yes'].values[0]
    elif re.search(pat2, resp) is not None:
        return filt_df['No'].values[0]
    else:
        return filt_df['Unsure'].values[0]
    #return filt_df['Full_Marks'].values[0]

logo_image = os.environ.get("LOGO")  # Replace with the actual logo image file name

st.sidebar.image(logo_image, width=200)
st.set_option('deprecation.showPyplotGlobalUse', False)

def main():
    st.title('Blue Badge Assessment Tool')
    uploaded_files = st.file_uploader("Choose PDF file(s)", accept_multiple_files=True)

    df = pd.read_excel(os.environ.get("EXCEL"),
                       names=['Questions', 'Reply', 'Full_Marks', 'Yes', 'No', 'Unsure', 'A', 'B'])

    qs_list = df[~df['Reply'].isnull()][['Questions', 'Full_Marks']].values
    df.fillna(0, inplace=True)

    extracted_texts = []
    name = []
    text = []
    for uploaded_file in uploaded_files:
        extracted_text = extract_text_from_pdf(uploaded_file)
        extracted_texts.append(extracted_text)
        text.append(extracted_text)
        name.append(uploaded_file.name)

    if extracted_texts:
        st.subheader("PDFs - Questions and Answers")
        total_marks = 0
        table_data = []
        question_counter = 0
        progress_bar_1 = st.progress(0)
        for i, extracted_text in enumerate(extracted_texts):
            st.subheader(f"PDF {i + 1} - Extracted Text")
            text_df = pd.DataFrame([extracted_text], columns=['Extracted Text'])
            st.dataframe(text_df)

            for question, marks in qs_list:
                if question_counter >= 5:
                    break

                prompt = f'''I will give you a document and a question. Based on the document, you must answer a question. 
                            You can only answer the question with three responses:
                            1. Yes
                            2. No
                            3. Unsure
                            You are not allowed to respond with anything else.

                            [start of question]
                            {question}
                            [end of question]

                            [start of document]
                            {extracted_text}
                            [end of document]

                            Remember, you cannot respond with anything other than "Yes", "No", or "Unsure".
                            '''
                response = yes_no_unsure(prompt)
                score_value = score(question, response, df)
                total_marks += score_value
                table_data.append([question, marks, response, score_value])

                question_counter += 1
                progress_bar_1.progress(question_counter / 5)

            if question_counter >= 5:
                break

        # Display the table of questions, answers, and marks for the first 5 questions
        st.subheader("Assessment Results - First 5 Questions")
        result_df = pd.DataFrame(table_data, columns=["Question", "Full Marks", "Answer", "Score"])
        st.dataframe(result_df)

        st.subheader("Total Marks - Round 1")
        st.write("# **", total_marks, "**")  # Use double asterisks for bold and bigger font


        st.subheader("Round 1 Result")
        if total_marks > 18:
            st.write("Round 1 passed")
        else:
            st.write("Round 1 failed")

        if question_counter < 5:
            st.warning("Not enough questions available for the first round.")
        time.sleep(21)
        if question_counter >= 5 and total_marks > 5:
            remaining_questions = qs_list[question_counter:]
            remaining_table_data = []
            progress_bar_2 = st.progress(0)
            for question, marks in remaining_questions:
                if question == 'How does the applicant describe the way they walk?':
                    prompt1 = f'''I will give you a document and a question. Based on the document, provide me
                    an answer to the question. You must answer in the following words:
                    1. Normal
                    2. Adequate
                    3. Poor
                    4. Very Poor
                    5. Other
                    You are not allowed to respond with anything else.
                    
                    [start of question]
                    {question}
                    [end of question]

                    [start of document]
                    {extracted_text}
                     [end of document]
                    '''
                    response = yes_no_unsure(prompt1)
                    score_value = score_different(question, response, df)
                    #total_marks += score_value
                    remaining_table_data.append([question, marks, response, score_value])

                    progress_bar_2.progress((question_counter + len(remaining_table_data)) / len(qs_list))

                elif question == 'How far is the applicant able to walk? ':
                    prompt2 = f'''I will give you a document and a question. Based on the document, provide me
                    an answer to the question.You must answer in the following words:
                    1. <30 m
                    2. <80 m
                    3. >80 m
                    You are not allowed to respond with anything else.
                    
                    [start of question]
                    {question}
                    [end of question]

                    [start of document]
                    {extracted_text}
                     [end of document]'''
                    response = yes_no_unsure(prompt2)
                    score_value = score_different(question, response, df)
                    #total_marks += score_value
                    remaining_table_data.append([question, marks, response, score_value])

                    progress_bar_2.progress((question_counter + len(remaining_table_data)) / len(qs_list))

                elif question == 'How long can you walk for, using a mobility aid, without stopping':
                    prompt3 = f'''I will give you a document and a question. Based on the document, provide me
                    an answer to the question.You must answer in the following words:
                    1. Can't walk
                    2. <1 min
                    3. 1-5 mins
                    4. 5-10 mins
                    5. >10 mins
                    You are not allowed to respond with anything else.
                    
                    [start of question]
                    {question}
                    [end of question]

                    [start of document]
                    {extracted_text}
                     [end of document]
                    
                    Remember, you cannot respond with anything other than  "Can't walk", "<1 min", "1-5 mins", "5-10 mins" and ">10 mins".
                    '''
                    response = yes_no_unsure(prompt3)
                    score_value = score_different(question, response, df)
                    #total_marks += score_value
                    remaining_table_data.append([question, marks, response, score_value])

                    progress_bar_2.progress((question_counter + len(remaining_table_data)) / len(qs_list))
                else:
                    prompt = f'''I will give you a document and a question. Based on the document, you must answer a question. 
                            You can only answer the question with three responses:
                            1. Yes
                            2. No
                            3. Unsure
                            You are not allowed to respond with anything else.

                            [start of question]
                            {question}
                            [end of question]

                            [start of document]
                            {extracted_text}
                            [end of document]

                            Remember, you cannot respond with anything other than "Yes", "No", or "Unsure".
                            '''
                    response = yes_no_unsure(prompt)
                    score_value = score(question,response, df)
                    total_marks += score_value
                    remaining_table_data.append([question, marks, response, score_value])

                progress_bar_2.progress((question_counter + len(remaining_table_data)) / len(qs_list))

            st.subheader("Assessment Results - Remaining Questions")
            remaining_result_df = pd.DataFrame(remaining_table_data, columns=["Question", "Full Marks", "Answer", "Score"])
            st.dataframe(remaining_result_df)

            st.subheader("Final Result")
            st.write("# **", total_marks, "**")
            if total_marks >= 100:
                display_success_icon()
                st.success("Passed - Agent should issue the Blue Badge")  # Success message with green checkmark icon
            else:
                st.write("Failed")
            
            threshold=0
            rejected_sections = remaining_result_df[remaining_result_df['Score'] == 0]

            st.subheader("Reasons for Rejection")
            if not rejected_sections.empty:
                reasons = generate_reasons_for_rejection(rejected_sections,threshold)
                for reason in reasons:
                    st.write(reason)
            else:
                st.write("No specific reasons for rejection found.")


if __name__ == "__main__":
    main()
