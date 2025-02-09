import requests
import json
import xml.etree.ElementTree as ET
import os
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Debugging: Print loaded environment variables
print("SENDGRID_API_KEY Loaded:", os.getenv("SENDGRID_API_KEY") is not None)
print("SENDER_EMAIL:", os.getenv("SENDER_EMAIL"))
print("RECIPIENT_EMAIL:", os.getenv("RECIPIENT_EMAIL"))

# PubMed API base URL
PUBMED_API_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
DETAILS_API_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Define AI-related query terms and journals
ONE_MONTH_AGO = (datetime.now() - timedelta(days=30)).strftime("%Y/%m/%d")
QUERY = f"(Artificial Intelligence OR Machine Learning OR Deep Learning OR Neural Networks OR Predictive Analytics) " \
        f"AND (J Am Coll Cardiol[Journal] OR Circulation[Journal] OR Eur Heart J[Journal] OR JAMA Cardiol[Journal] " \
        f"OR Nat Cardiovasc Res[Journal] OR Heart Rhythm[Journal] OR Europace[Journal] OR JACC Clin Electrophysiol[Journal] " \
        f"OR Circ Arrhythm Electrophysiol[Journal] OR J Cardiovasc Electrophysiol[Journal]) " \
        f"AND ({ONE_MONTH_AGO}[PDAT] : {datetime.now().strftime('%Y/%m/%d')}[PDAT])"

# Fetch articles from PubMed
def fetch_pubmed_articles(max_results=20):
    params = {
        "db": "pubmed",
        "term": QUERY,
        "retmax": max_results,
        "retmode": "json"
    }
    response = requests.get(PUBMED_API_URL, params=params)
    if response.status_code == 200:
        return response.json()["esearchresult"]["idlist"]
    else:
        print("Error fetching articles from PubMed.")
        return []

# Fetch details for given article IDs
def fetch_article_details(article_ids):
    params = {
        "db": "pubmed",
        "id": ",".join(article_ids),
        "retmode": "xml"
    }
    response = requests.get(DETAILS_API_URL, params=params)
    if response.status_code == 200:
        return parse_article_details(response.text)
    else:
        print("Error fetching article details.")
        return []

# Parse XML response to extract article details
def parse_article_details(xml_data):
    articles = []
    root = ET.fromstring(xml_data)
    for article in root.findall(".//PubmedArticle"):
        title = article.find(".//ArticleTitle").text if article.find(".//ArticleTitle") is not None else "No Title"
        abstract = article.find(".//AbstractText").text if article.find(".//AbstractText") is not None else "No Abstract"
        pub_date = article.find(".//PubDate/Year").text if article.find(".//PubDate/Year") is not None else "Unknown Date"
        journal = article.find(".//Journal/Title").text if article.find(".//Journal/Title") is not None else "Unknown Journal"
        articles.append({
            "title": title,
            "abstract": abstract,
            "pub_date": pub_date,
            "journal": journal
        })
    return articles

# Format results for weekly email summary
def format_results(articles):
    email_content = "Weekly AI in Cardiology Research Digest\n\n"
    for article in articles:
        email_content += f"Title: {article['title']}\n"
        email_content += f"Journal: {article['journal']}\n"
        email_content += f"Published: {article['pub_date']}\n"
        email_content += f"Abstract: {article['abstract'][:500]}...\n"  # Limit abstract to 500 characters
        email_content += "-" * 80 + "\n"
    return email_content

# Send email using SendGrid API
def send_email(formatted_content, recipient_email):
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")

    message = Mail(
        from_email=sender_email,
        to_emails=recipient_email,
        subject="Weekly AI in Cardiology Research Digest",
        plain_text_content=formatted_content)

    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        print("Email sent successfully.", response.status_code)
    except Exception as e:
        print("Error sending email:", e)

if __name__ == "__main__":
    article_ids = fetch_pubmed_articles()
    if article_ids:
        print(f"Found {len(article_ids)} articles from the last month. Fetching details...")
        articles = fetch_article_details(article_ids)
        formatted_email = format_results(articles)
        send_email(formatted_email, os.getenv("RECIPIENT_EMAIL"))
    else:
        print("No articles found in the last month.")
