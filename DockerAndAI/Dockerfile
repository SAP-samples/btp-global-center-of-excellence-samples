FROM python:3.12-slim

ENV PORT=5000
#create group with a predetermined GID of 2000 and user
RUN groupadd -g 2000 sampleapp && useradd -u 1000 -g sampleapp -m sampleapp

EXPOSE $PORT
#switch current user from root to the new user
USER sampleapp:sampleapp

COPY *.py /home/sampleapp/

WORKDIR /home/sampleapp/

ENV PATH "/venv/bin:${PATH}" 
ENTRYPOINT [ "gunicorn", "--preload", "sampleapp:app" ]