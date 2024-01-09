FROM python:3.9-slim-buster
WORKDIR app/
COPY . .
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip  \
    pip install -r requirements.txt
EXPOSE 8501
ENTRYPOINT ["streamlit", "run"]
CMD ["failed_03.py"]