from fastmcp import FastMCP
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.embeddings.base import Embeddings
from sentence_transformers import SentenceTransformer
from pathlib import Path
import asyncio

retriever = None

mcp = FastMCP('rag_based_server')

# Create custom embeddings class with async support
class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts):
        return self.model.encode(texts).tolist()
    
    def embed_query(self, text):
        return self.model.encode([text])[0].tolist()
    
    async def aembed_documents(self, texts):
        """Async version of embed_documents"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_documents, texts)
    
    async def aembed_query(self, text):
        """Async version of embed_query"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_query, text)


async def load_split_embedded(path: str):
    """Load and split PDF into chunks"""
    loop = asyncio.get_event_loop()
    
    # PDF LOADED HERE - run in executor since PyPDFLoader.load() is synchronous
    pdf = PyPDFLoader(path)
    pdf_loaded = await loop.run_in_executor(None, pdf.load)

    # PDF SPLIT AND CHUNKS ARE CREATED HERE - run in executor since split_documents is synchronous
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=300)
    splitted_chunks = await loop.run_in_executor(None, splitter.split_documents, pdf_loaded)
    
    return splitted_chunks


async def create_vectorstore(chunks, embeddings):
    """Create FAISS vectorstore asynchronously"""
    loop = asyncio.get_event_loop()
    
    # Run FAISS creation in executor (it's CPU-intensive)
    vectorstore = await loop.run_in_executor(
        None, 
        FAISS.from_documents, 
        chunks, 
        embeddings
    )
    
    return vectorstore


async def save_vectorstore(vectorstore, path: str = "faiss_index"):
    """Save vectorstore to disk asynchronously"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, vectorstore.save_local, path)
    print(f"FAISS vector store saved to '{path}' folder!")


async def main():
    """Main async function orchestrating the RAG pipeline"""
    
    # Step 1: Load and split PDF
    print("Loading and splitting PDF...")
    chunks = await load_split_embedded(
        r'A:\AI_Projects\AI Conversational Agent\ml_pdf_for_rag.pdf'
    )
    print(f"Created {len(chunks)} chunks")

    # Step 2: Initialize embeddings
    print("Initializing embeddings model...")
    embeddings = SentenceTransformerEmbeddings()

    # Step 3: Create FAISS vector store
    print("Creating FAISS vector store...")
    vectorstore = await create_vectorstore(chunks, embeddings)

    # Step 4: Save to disk
    print("Saving vector store...")
    await save_vectorstore(vectorstore)
    
    # Step 5: Create retriever
    retriever = vectorstore.as_retriever(
        search_type='similarity', 
        search_kwargs={'k': 4}
    )
    
    print("RAG pipeline completed successfully!")
    return retriever


@mcp.tool
async def rag_server_code(query: str) -> str:
    """
    Retrieved relevant information from the pdf documents.
    Use this tool when the user asks factual / conceptual questions
    that might be answered from the stored documents
    """
    global retriever
    if retriever is None:
        return "RAG system not initialized."
    
    result = await retriever.ainvoke(query)

    context = [ret.page_content for ret in result]
    metadata = [ret.metadata for ret in result]

    # Format as string
    response = f"Query: {query}\n\nRelevant Context:\n"
    for i, ctx in enumerate(context, 1):
        response += f"{i}. {ctx}\n"
    response += f"\nMetadata: {metadata}"
    
    return response

# Run the async function
if __name__ == "__main__":
    retriever = asyncio.run(main())
    mcp.run()