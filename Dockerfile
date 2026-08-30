FROM python:3.10.2-alpine3.15

# Create directories
RUN mkdir -p /root/workspace/src

# Copy project files
COPY requirements.txt /root/workspace/src/
COPY web_scraping_sample.py /root/workspace/src/
COPY blog_scraper.py /root/workspace/src/

# Switch to project directory
WORKDIR /root/workspace/src

# Install required packages
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
