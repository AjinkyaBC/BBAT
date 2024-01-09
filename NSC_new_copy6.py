import time
import streamlit as st
import fitz
import pandas as pd
import openai
import re
import streamlit.components.v1 as components
import json
from dotenv import load_dotenv
import os

load_dotenv(".env")


openai.api_type = "azure"
openai.api_base = "https://bc-api-management-uksouth.azure-api.net"
openai.api_version = "2023-03-15-preview"
openai.log = "debug"
# Set up OpenAI API credentials
openai.api_key = os.getenv("openai_api_key")


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
        temperature=0,
        max_tokens=1200,
        top_p=1
    )
    time.sleep(2)
    return response['choices'][0]['message']['content']

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

def score(txt, resp, df):
    filt_df = df[df['Questions'] == txt]
    pat1 = 'Yes'
    pat2 = 'No'
    if re.search(pat1, resp) is not None:
        return filt_df['Yes'].values[0]
    elif re.search(pat2, resp) is not None:
        return filt_df['No'].values[0]
    else:
        return filt_df["Don't Know"].values[0]
    #return filt_df['Full_Marks'].values[0]

def score_different(txt, resp, df):
    filt_df = df[df['Questions'] == txt]
    
    if txt == 'Permanent disability or condition (expected not to improve for at least 3 years)?':
        pat1 = 'Yes'
        pat2 = 'No'
        
        if re.search(pat1, resp) is not None:
            return filt_df['Yes'].values[0]
        elif re.search(pat2, resp) is not None:
            return filt_df['No'].values[0]
        # elif re.search(pat3, resp) is not None:
        #     return filt_df["Don't Know"].values[0]

    elif txt == "Do your health conditions affect your walking all the time?":
        pat1 = 'Yes'
        pat2 = 'No'
        
        if re.search(pat1, resp) is not None:
            return filt_df['Yes'].values[0]
        elif re.search(pat2, resp) is not None:
            return filt_df['No'].values[0]
        
    elif txt == "Have you seen a healthcare professional for any falls in the last 12 months?":
        pat1 = 'Yes'
        pat2 = 'No'
        
        if re.search(pat1, resp) is not None:
            return filt_df['Yes'].values[0]
        elif re.search(pat2, resp) is not None:
            return filt_df['No'].values[0]

        
    elif txt == 'For how long can the applicant walk?':
        pat1 = "Can't walk"
        pat2 = '<1 min'
        pat3 = '1-5 mins'
        pat4 = '5-10 mins'
        pat5 = '>10 mins'
        if re.search(pat1, resp.lower()) is not None:
            return filt_df['Yes'].values[0]
        elif re.search(pat2, resp.lower()) is not None:
            return filt_df['No'].values[0]
        elif re.search(pat3, resp.lower()) is not None:
            return filt_df["Don't Know"].values[0]
        elif re.search(pat4, resp.lower()) is not None:
            return filt_df['A'].values[0]
        elif re.search(pat5, resp.lower()) is not None:
            return filt_df['B'].values[0]
        
    elif txt == 'How far is the applicant able to walk? ':
        pat1 = '<30 m'
        pat2 = '<80 m'
        pat3 = '>80 m'
        pat4 = "Don't Know"
        if re.search(pat1, resp) is not None:
            return filt_df['Yes'].values[0]
        elif re.search(pat2, resp) is not None:
            return filt_df['No'].values[0]
        elif re.search(pat3, resp) is not None:
            return filt_df["Don't Know"].values[0]
        elif re.search(pat4, resp.lower()) is not None:
            return filt_df['A'].values[0]
        else:
            return 0
        
    elif txt == 'Do you have help to get around?':
        pat1 = 'Yes'
        pat2 = 'No'
        pat3 = "Don't Know"
        if re.search(pat1, resp) is not None:
            return filt_df['Yes'].values[0]
        elif re.search(pat2, resp) is not None:
            return filt_df['No'].values[0]
        elif re.search(pat3, resp) is not None:
            return filt_df["Don't Know"].values[0]
        
def generate_reasons_for_rejection(sections):
    reasons = []
    response3 = openai.ChatCompletion.create(
        engine="gpt-4",
        messages=[{"role": "system", "content": sections}],
        temperature=0.07,
        max_tokens=1200,
        top_p=1
    )
    rejection_reasons = response3['choices'][0]['message']['content']
    return rejection_reasons

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

logo_image = "Agilisys-Logo-Black-RGB.png"  # Replace with the actual logo image file name

st.sidebar.image(logo_image, width=200)
st.set_option('deprecation.showPyplotGlobalUse', False)


st.title('Blue Badge Assessment Tool')
uploaded_files = st.file_uploader("Choose PDF file(s)", accept_multiple_files=True)

df = pd.read_excel('NSC_updated (2).xlsb',
                    names=['Questions', 'Reply', 'Full_Marks', 'Yes', 'No', "Don't Know", 'A', 'B'])

qs_list = df[~df['Reply'].isnull()][['Questions', 'Full_Marks']].values
# print(qs_list)
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
            
            
            if question == 'Permanent disability or condition (expected not to improve for at least 3 years)?':
                prompt2 = f'''I will give you a document and a question. Based on the document, provide me
                an answer to the question.You must answer in the following words:
                1. Yes
                2. No
                You are not allowed to respond with anything else.
                
                [start of question]
                {question}
                [end of question]

                [start of document]
                {extracted_text}
                    [end of document]
                    Remember, you cannot respond with anything other than "Yes" or "No".
                '''
                response = yes_no_unsure(prompt2)
                score_value = score_different(question, response, df)
                total_marks += score_value
                table_data.append([question, marks, response, score_value])
                question_counter += 1
                progress_bar_1.progress(question_counter / 6)
                
            
            elif question == 'Do your health conditions affect your walking all the time?':
                prompt2 = f'''I will give you a document and a question. Based on the document, provide me
                an answer to the question.You must answer in the following words:
                1. Yes
                2. No
                You are not allowed to respond with anything else.
                
                [start of question]
                {question}
                [end of question]

                [start of document]
                {extracted_text}
                    [end of document]
                    Remember, you cannot respond with anything other than "Yes" or "No".
                '''
                response = yes_no_unsure(prompt2)
                score_value = score_different(question, response, df)
                total_marks += score_value
                table_data.append([question, marks, response, score_value])
                question_counter += 1
                progress_bar_1.progress(question_counter / 6)
                


            elif question == 'Have you seen a healthcare professional for any falls in the last 12 months?':
                prompt2 = f'''I will give you a document and a question. Based on the document, provide me
                an answer to the question.You must answer in the following words:
                1. Yes
                2. No
                You are not allowed to respond with anything else.
                
                [start of question]
                {question}
                [end of question]

                [start of document]
                {extracted_text}
                    [end of document]
                    Remember, you cannot respond with anything other than "Yes" or "No".
                '''
                response = yes_no_unsure(prompt2)
                score_value = score_different(question, response, df)
                total_marks += score_value
                table_data.append([question, marks, response, score_value])
                question_counter+=1
                progress_bar_1.progress(question_counter / 6)
                
            
            elif question == 'For how long can the applicant walk?':
                prompt1 = f'''I will give you a document and a question. Based on the document, provide me
                an answer to the question. You must answer in the following words:
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
                
                '''
                response = yes_no_unsure(prompt1)
                score_value = score_different(question, response, df)
                total_marks += score_value
                table_data.append([question, marks, response, score_value])
                question_counter+=1

                progress_bar_1.progress(question_counter / 6)
                

            elif question == 'How far is the applicant able to walk? ':
                prompt2 = f'''I will give you a document and a question. Based on the document, provide me
                an answer to the question.You must answer in the following words:
                1. <30 m
                2. <80 m
                3. >80 m
                4. Don't Know
                
                You are not allowed to respond with anything else.
                
                [start of question]
                {question}
                [end of question]

                [start of document]
                {extracted_text}
                    [end of document]
                
                Remember, you cannot respond with anything other than "<30 m", "<80 m", ">80 m" or "Don't Know".
                If the distance the applicant is able to walk is not explicitly mentioned in the {extracted_text} in metres then answer it only as "Don't Know".
                If the answer to the {question} is "Don't Know" then the {score_value} should be 0.
                


                '''
                response = yes_no_unsure(prompt2)
                score_value = score_different(question, response, df)
                total_marks += score_value
                table_data.append([question, marks, response, score_value])
                question_counter += 1
                progress_bar_1.progress(question_counter / 6)
                
            
            elif question == 'Do you have help to get around?':
                prompt2 = f'''I will give you a document and a question. Based on the document, provide me
                an answer to the question.You must answer in the following words:
                1. Yes
                2. No
                3. Don't Know
                You are not allowed to respond with anything else.
                
                [start of question]
                {question}
                [end of question]

                [start of document]
                {extracted_text}
                    [end of document]
                '''
                response = yes_no_unsure(prompt2)
                score_value = score_different(question, response, df)
                table_data.append([question, marks, response, score_value])
                total_marks += score_value
                question_counter += 1
                progress_bar_1.progress(question_counter / 6)

            elif question_counter == 6:
                break
        
        st.subheader("Assessment Results - First 6 Questions")
        result_df = pd.DataFrame(table_data, columns=["Question", "Full Marks", "Answer", "Score"])
        result_df.drop(labels="Full Marks", axis=1, inplace=True)
        st.dataframe(result_df)

        st.subheader("Total Marks - Round 1")
        st.write("# **", total_marks, "**")  # Use double asterisks for bold and bigger font


        st.subheader("Round 1 Result")
        if total_marks >= 40:
            st.success("Round 1 passed")
        else:
            st.error("Round 1 failed")
            st.subheader("Reason for Rejection:")
            st.subheader("The applicant hasn't scored 40 marks or above to clear Round 1.")
        time.sleep(21)

        if question_counter >= 5 and total_marks >= 40:
            remaining_questions = qs_list[question_counter:]
            # print(remaining_questions)
            remaining_table_data = []
            progress_bar_2 = st.progress(0)
            # progress_bar_2 = st.empty()
            for question, marks in remaining_questions:
                prompt = f'''I will give you a document and a question. Based on the document, you must answer a question. 
                        You can only answer the question with three responses:
                        1. Yes
                        2. No
                        3. Don't Know
                        
                        You are not allowed to respond with anything else.

                        [start of question]
                        {question}
                        [end of question]

                        [start of document]
                        {extracted_text}
                        [end of document]

                        Remember, you cannot respond with anything other than "Yes", "No" or "Don't Know".
                        If the {extracted_text} doesn't have any information asked in the question, then
                        kindly answer it as "Don't know" only. Answer it only as "Yes" or "No" only and only if the 
                        {extracted_text} has an answer with respect to the question.
                        '''
                response = yes_no_unsure(prompt)
                score_value = score(question, response, df)
                
                remaining_table_data.append([question, marks, response, score_value])
                total_marks += score_value

                progress_bar_2.progress((question_counter + len(remaining_table_data)) / len(qs_list))


        # Display the table of questions, answers, and marks for the first 5 questions
            st.subheader("Assessment Results")
            remaining_result_df = pd.DataFrame(remaining_table_data, columns=["Question", "Full Marks", "Answer", "Score"])
            remaining_result_df.drop(labels="Full Marks", axis=1, inplace=True)
            st.dataframe(remaining_result_df)

            st.subheader("Total Marks")
            st.write("# **", total_marks, "**")  # Use double asterisks for bold and bigger font
            if total_marks >= 60:
                st.success("Passed - Agent should issue the Blue Badge")
            elif 40 <= total_marks < 60:
                st.success('Team analysis required')
            else:
                st.error("Failed")
            
            rejected_sections = remaining_result_df[remaining_result_df['Score'] == 0]

            # st.subheader("Reasons for Rejection:")
            # if not rejected_sections.empty:
            #     rejection_prompt = f'''I want you to summarize all the reasons for rejections:{rejected_sections}
            # into a single summarized paragraph which states all the possible reasons for which the applicant was 
            # refused the blue badge. Keep the summary simple and to the point so that the agent can understand it easily.'''
            #     response3 = generate_reasons_for_rejection(rejection_prompt)
            #     st.write(response3)
            # else:
            #     st.write("No specific reasons for rejection found.")

