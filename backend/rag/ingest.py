"""
Ingest knowledge base documents into the FAISS vector store.
Run once before starting the server:
    python backend/rag/ingest.py
"""
import os
from pathlib import Path
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from loguru import logger

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.config import (
    KNOWLEDGE_BASE_PATH, VECTOR_STORE_PATH,
    EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP,
)

KB_PATH = Path(KNOWLEDGE_BASE_PATH)
VS_PATH = Path(VECTOR_STORE_PATH)


def ingest():
    logger.info(f"Loading documents from: {KB_PATH}")
    KB_PATH.mkdir(parents=True, exist_ok=True)

    # Create sample KB if empty
    _seed_knowledge_base()

    loader = DirectoryLoader(str(KB_PATH), glob="**/*.txt", loader_cls=TextLoader)
    docs   = loader.load()
    logger.info(f"Loaded {len(docs)} document(s).")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(docs)
    logger.info(f"Split into {len(chunks)} chunk(s).")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    store = FAISS.from_documents(chunks, embeddings)

    VS_PATH.mkdir(parents=True, exist_ok=True)
    store.save_local(str(VS_PATH))
    logger.success(f"Vector store saved to {VS_PATH}")


def _seed_knowledge_base():
    """Create sample support documents so the demo works out of the box."""
    samples = {
        "shipping_policy.txt": """
# Shipping Policy

Standard shipping takes 5-7 business days. Express shipping (2-3 days) is available for $12.99.
Free shipping on all orders over $50. International shipping available to 30+ countries.

To track your order, visit our website and enter your order number in the tracking portal.
You will also receive a tracking email once your order ships.

Orders placed before 2 PM EST on weekdays ship same day. Weekend orders ship Monday.
""",
        "returns_refunds.txt": """
# Returns & Refunds Policy

We accept returns within 30 days of purchase. Items must be unused and in original packaging.

To initiate a return:
1. Log into your account and navigate to Order History.
2. Select the item you wish to return and click "Start Return".
3. Print the prepaid return label provided.
4. Drop off the package at any UPS location.

Refunds are processed within 3-5 business days after we receive your return.
Refunds are credited to your original payment method.

For exchanges, please place a new order and return the unwanted item separately.
""",
        "account_help.txt": """
# Account & Login Help

Forgot your password? Click "Forgot Password" on the login page and enter your email address.
You will receive a reset link within 5 minutes. Check your spam folder if you don't see it.

To update your email address, go to Account Settings > Personal Info > Edit Email.
Note: You must verify the new email address before the change takes effect.

For account lockouts (after 5 failed attempts), please contact support@company.com.
Two-factor authentication (2FA) is available under Account Settings > Security.
""",
        "product_faq.txt": """
# Product FAQs

Q: What is your warranty policy?
A: All products come with a 1-year limited warranty covering manufacturing defects.

Q: Do you offer product bundles?
A: Yes! Visit our Bundles page for discounted multi-product packages, saving up to 25%.

Q: Are your products compatible with third-party accessories?
A: Our products follow industry-standard connectors. Compatibility details are on each product page.

Q: Where can I find product manuals?
A: PDF manuals are available on the product page under the "Downloads" tab.

Q: Can I cancel my order?
A: Orders can be cancelled within 1 hour of placement. After that, please wait for delivery and use our returns process.
""",
    }
    for filename, content in samples.items():
        path = KB_PATH / filename
        if not path.exists():
            path.write_text(content.strip())
            logger.info(f"Created sample: {filename}")


if __name__ == "__main__":
    ingest()
