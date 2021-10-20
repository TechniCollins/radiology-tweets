FROM python:3.9.5-slim-buster

MAINTAINER  TechniCollins "technicollins.business@gmail.com"

ENV HOME /root
ENV APP_HOME /application/
ENV C_FORCE_ROOT=true
ENV PYTHONUNBUFFERED 1

RUN mkdir -p $APP_HOME
WORKDIR $APP_HOME

# Install pip packages
ADD ./requirements.txt .
RUN pip install -r requirements.txt
RUN rm requirements.txt


# Copy code into Image
ADD ./radiology_twitter/ $APP_HOME

# collect static files
# RUN $APP_HOME/manage.py collectstatic
