"""
Seed script to add sample documents to the IntelliStream database.
Run this after setting up the database schema in Supabase.

Usage:
    cd backend
    python scripts/seed_documents.py
"""

import asyncio
import httpx

API_URL = "http://localhost:8000/api/documents"

SAMPLE_DOCUMENTS = [
    {
        "title": "NVIDIA Q4 2024 Earnings Report",
        "content": """NVIDIA reported record revenue of $22.1 billion for Q4 2024, marking a 265% increase
year-over-year. The company's data center segment was the primary growth driver, generating $18.4 billion
in revenue with a staggering 409% year-over-year growth. This unprecedented demand is fueled by enterprises
and cloud providers racing to deploy AI infrastructure. CEO Jensen Huang stated that generative AI has
reached a tipping point, with demand for NVIDIA's Hopper and upcoming Blackwell architecture GPUs
far outpacing supply. The gaming segment also showed resilience with $2.9 billion in revenue.
NVIDIA's market capitalization has surpassed $1.8 trillion, making it one of the most valuable
companies globally. Analysts project continued momentum as AI adoption accelerates across industries.""",
        "source_url": "https://investor.nvidia.com/news",
        "source_type": "news"
    },
    {
        "title": "OpenAI GPT-4 Turbo and Future Models",
        "content": """OpenAI continues to push the boundaries of large language models with GPT-4 Turbo,
featuring a 128K context window and improved instruction following. The model shows significant
improvements in complex reasoning, coding tasks, and multimodal understanding. OpenAI has also
announced the development of GPT-5, expected to feature enhanced reasoning capabilities, better
long-term memory, and more sophisticated multimodal understanding including video. The company
is focusing on AI safety and alignment, implementing new red-teaming protocols and developing
interpretability tools. OpenAI's API pricing has been reduced by 3x for GPT-4 Turbo, making
advanced AI more accessible to developers. The company's valuation has reached $80 billion,
with major investments from Microsoft and other technology leaders.""",
        "source_url": "https://openai.com/blog",
        "source_type": "research"
    },
    {
        "title": "Cloud Computing Market Trends 2024-2028",
        "content": """The global cloud computing market is projected to reach $1.5 trillion by 2028,
growing at a CAGR of 15.7%. Key drivers include AI workload acceleration, enterprise digital
transformation, and the shift to hybrid cloud architectures. AWS maintains market leadership
with 32% share, followed by Microsoft Azure at 23% and Google Cloud at 10%. The emergence of
specialized AI clouds and GPU-as-a-Service offerings is reshaping the competitive landscape.
Edge computing integration is growing rapidly, with enterprises deploying distributed
infrastructure for low-latency AI inference. Security and compliance remain top priorities,
driving adoption of sovereign cloud solutions. Multi-cloud strategies are now standard for
73% of enterprises, up from 58% in 2022.""",
        "source_url": "https://www.gartner.com/cloud-research",
        "source_type": "research"
    },
    {
        "title": "Large Language Model Developments in 2024",
        "content": """2024 has seen remarkable advances in large language models across multiple dimensions.
Key developments include: 1) Mixture of Experts (MoE) architectures becoming mainstream, enabling
more efficient scaling as seen in Mixtral 8x7B and GPT-4's rumored architecture. 2) Long context
windows exceeding 1 million tokens with models like Gemini 1.5 Pro. 3) Multimodal capabilities
expanding to include video understanding, real-time audio, and 3D spatial reasoning. 4)
Open-source models closing the gap with proprietary solutions - Llama 3, Mistral, and Qwen
achieving near-GPT-4 performance. 5) Reasoning improvements through chain-of-thought and
self-consistency techniques. 6) Smaller, more efficient models achieving strong performance
through better training data and techniques. The focus is shifting from pure scale to
efficiency, safety, and specialized capabilities.""",
        "source_url": "https://arxiv.org/ai-research",
        "source_type": "research"
    },
    {
        "title": "AI Chip Market Competition Intensifies",
        "content": """The AI accelerator market is experiencing unprecedented competition as major
tech companies challenge NVIDIA's dominance. AMD's MI300X chips are gaining traction with
hyperscalers, offering competitive performance at lower prices. Intel's Gaudi 3 promises
40% better performance than its predecessor. Google's TPU v5e is powering Gemini and
is available to cloud customers. Amazon's Trainium2 chips aim to reduce AI training costs
by 50%. Apple's M3 Ultra integrates powerful neural engines for on-device AI. Startups like
Cerebras, Graphcore, and SambaNova are pursuing novel architectures. The market is expected
to reach $80 billion by 2027. NVIDIA maintains its lead through CUDA ecosystem lock-in and
the upcoming Blackwell architecture. The chip shortage for AI hardware is expected to
persist through 2025 as demand continues to outstrip manufacturing capacity.""",
        "source_url": "https://www.techinsights.com",
        "source_type": "news"
    },
    {
        "title": "Enterprise AI Adoption Trends",
        "content": """Enterprise AI adoption has reached an inflection point in 2024, with 65% of
companies now using AI in at least one business function, up from 50% in 2023. Key trends
include: 1) RAG (Retrieval-Augmented Generation) becoming the standard for enterprise
knowledge systems, reducing hallucinations and improving accuracy. 2) AI agents and
autonomous workflows emerging for customer service, coding, and data analysis. 3)
Fine-tuning and domain adaptation enabling specialized models for healthcare, legal, and
finance sectors. 4) AI governance and compliance frameworks maturing with new regulations
like the EU AI Act. 5) ROI measurement improving with clearer metrics for productivity gains.
Challenges remain around data quality, integration with legacy systems, and talent shortage.
The average enterprise AI project now shows positive ROI within 14 months, down from
24 months in 2022.""",
        "source_url": "https://www.mckinsey.com/ai-insights",
        "source_type": "research"
    },
    {
        "title": "Vector Database Market Growth",
        "content": """Vector databases have emerged as critical infrastructure for AI applications,
with the market growing 300% year-over-year. Leading solutions include Pinecone, Weaviate,
Milvus, Qdrant, and pgvector for PostgreSQL. Key capabilities include approximate nearest
neighbor (ANN) search, hybrid search combining vectors with metadata filtering, and
real-time indexing. Major cloud providers are adding native vector search: AWS OpenSearch,
Azure Cosmos DB, and Google AlloyDB now support vector operations. Use cases extend beyond
semantic search to recommendation systems, anomaly detection, and multimodal retrieval.
Performance benchmarks show sub-millisecond query times for billion-scale indexes with
proper optimization. The market is expected to reach $3.5 billion by 2028 as AI applications
requiring similarity search proliferate.""",
        "source_url": "https://www.dbta.com/vector-databases",
        "source_type": "research"
    }
]


async def seed_documents():
    """Add sample documents to the database via API."""
    print("Starting document seeding...")
    print(f"API URL: {API_URL}")
    print(f"Documents to add: {len(SAMPLE_DOCUMENTS)}")
    print("-" * 50)

    async with httpx.AsyncClient(timeout=60.0) as client:
        success_count = 0

        for i, doc in enumerate(SAMPLE_DOCUMENTS, 1):
            try:
                print(f"\n[{i}/{len(SAMPLE_DOCUMENTS)}] Adding: {doc['title'][:50]}...")

                response = await client.post(API_URL, json=doc)

                if response.status_code == 200:
                    result = response.json()
                    print(f"    Success! ID: {result.get('id', 'N/A')}")
                    success_count += 1
                elif response.status_code == 500 and "429" in response.text:
                    print(f"    Rate limited - waiting 3 seconds...")
                    await asyncio.sleep(3)
                    # Retry once
                    response = await client.post(API_URL, json=doc)
                    if response.status_code == 200:
                        result = response.json()
                        print(f"    Retry Success! ID: {result.get('id', 'N/A')}")
                        success_count += 1
                    else:
                        print(f"    Retry failed: {response.status_code}")
                else:
                    print(f"    Failed! Status: {response.status_code}")
                    print(f"    Response: {response.text[:200]}")

                # Add delay between requests to avoid rate limiting
                await asyncio.sleep(1)

            except Exception as e:
                print(f"    Error: {str(e)}")

        print("\n" + "=" * 50)
        print(f"Seeding complete! {success_count}/{len(SAMPLE_DOCUMENTS)} documents added.")

        if success_count < len(SAMPLE_DOCUMENTS):
            print("\nNote: Some documents failed. Make sure:")
            print("  1. Backend server is running (uvicorn app.main:app --port 8000)")
            print("  2. Database schema is set up in Supabase")
            print("  3. All API keys are configured in .env")


async def check_health():
    """Check if the API is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("API health check: OK")
                return True
    except Exception as e:
        print(f"API health check failed: {e}")
    return False


async def main():
    """Main entry point."""
    print("=" * 50)
    print("IntelliStream Document Seeder")
    print("=" * 50)

    # Check API health first
    if not await check_health():
        print("\nError: Backend API is not running!")
        print("Start it with: cd backend && .venv/Scripts/uvicorn.exe app.main:app --port 8000")
        return

    await seed_documents()

    print("\nYou can now test the RAG system by asking questions like:")
    print('  - "What are the latest trends in AI?"')
    print('  - "Tell me about NVIDIA earnings"')
    print('  - "How is the cloud computing market growing?"')


if __name__ == "__main__":
    asyncio.run(main())
