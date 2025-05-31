"""
Demo script showing how Perplexity tools work in the WhatsApp workflow
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def demo_tool_descriptions():
    """Show the tool descriptions and how they would be used."""
    print("🔍 PERPLEXITY SEARCH TOOLS FOR WHATSAPP WORKFLOW")
    print("=" * 70)
    
    from agents.workflows.whatsapp.integrations.perplexity_search import (
        search_person_and_generate_intro,
        search_company_overview,
    )
    
    print("1. PERSON SEARCH AND INTRODUCTION TOOL")
    print("-" * 50)
    print(f"Tool Name: {search_person_and_generate_intro.name}")
    print(f"Description: {search_person_and_generate_intro.description}")
    print("\nParameters:")
    for param_name, param_info in search_person_and_generate_intro.args.items():
        print(f"  - {param_name}: {param_info}")
    
    print("\n" + "=" * 70)
    print("2. COMPANY OVERVIEW TOOL")
    print("-" * 50)
    print(f"Tool Name: {search_company_overview.name}")
    print(f"Description: {search_company_overview.description}")
    print("\nParameters:")
    for param_name, param_info in search_company_overview.args.items():
        print(f"  - {param_name}: {param_info}")

def demo_usage_scenarios():
    """Show different usage scenarios for the tools."""
    print("\n" + "🎯 USAGE SCENARIOS")
    print("=" * 70)
    
    scenarios = [
        {
            "title": "Scenario 1: Networking at a Conference",
            "user_message": "I just met John Smith from Microsoft at a conference. Can you help me prepare for a follow-up?",
            "tool_call": "search_person_and_generate_intro",
            "parameters": {
                "person_name": "John Smith",
                "company_name": "Microsoft",
                "user_id": "user_123"
            },
            "memory_context": [
                "I work as a software engineer at TechCorp",
                "I specialize in cloud infrastructure and DevOps",
                "I'm interested in learning about Azure and Microsoft technologies"
            ]
        },
        {
            "title": "Scenario 2: Sales Prospect Research",
            "user_message": "I have a call with the CTO of Stripe next week. What should I know?",
            "tool_call": "search_person_and_generate_intro",
            "parameters": {
                "person_name": "David Singleton",
                "company_name": "Stripe",
                "user_id": "user_456"
            },
            "memory_context": [
                "I work in sales at PaymentTech Solutions",
                "I focus on enterprise payment integration solutions",
                "I have experience with financial services APIs"
            ]
        },
        {
            "title": "Scenario 3: Investment Research",
            "user_message": "Tell me about OpenAI as a company before my investor meeting",
            "tool_call": "search_company_overview",
            "parameters": {
                "company_name": "OpenAI",
                "user_id": "user_789"
            },
            "memory_context": [
                "I'm a venture capitalist at AI Ventures",
                "I focus on AI and machine learning investments",
                "I have a background in computer science and business"
            ]
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{scenario['title']}")
        print("-" * 50)
        print(f"💬 User says: \"{scenario['user_message']}\"")
        print(f"🔧 Tool called: {scenario['tool_call']}")
        print(f"📝 Parameters: {scenario['parameters']}")
        print(f"🧠 User memory context:")
        for memory in scenario['memory_context']:
            print(f"   • {memory}")
        
        print(f"\n🤖 AI would:")
        if scenario['tool_call'] == 'search_person_and_generate_intro':
            print("   1. Search Perplexity for the person's professional background")
            print("   2. Retrieve user's memories for context")
            print("   3. Generate personalized introduction strategy")
            print("   4. Store the research in user's memory")
        else:
            print("   1. Search Perplexity for comprehensive company information")
            print("   2. Store the research in user's memory")
            print("   3. Provide business model, financials, leadership info")

def demo_expected_output():
    """Show what the expected output would look like."""
    print("\n" + "📄 EXPECTED OUTPUT EXAMPLE")
    print("=" * 70)
    
    print("For: search_person_and_generate_intro('Satya Nadella', 'user_123', 'Microsoft')")
    print("-" * 70)
    
    example_output = """
PROFESSIONAL OVERVIEW:
Satya Nadella is the CEO of Microsoft Corporation, a position he has held since 2014. 
Prior to becoming CEO, he served as Executive Vice President of Microsoft's Cloud and 
Enterprise group. He has a background in computer science and has been instrumental in 
Microsoft's transformation to cloud computing with Azure. Under his leadership, Microsoft 
has focused on AI, cloud services, and productivity tools.

USER CONTEXT FROM MEMORIES:
I work as a software engineer at TechCorp focusing on AI and machine learning
I have 5 years of experience in Python and data science
I'm interested in startup investments and technology trends

PERSONALIZED INTRODUCTION STRATEGY:
Key connection points:
- Both have technical backgrounds in software engineering
- Shared interest in AI and machine learning technologies
- Microsoft's AI initiatives align with your expertise

Suggested opening line:
"Hi Satya, I enjoyed our conversation at [event]. As a software engineer working in AI/ML, 
I'm fascinated by Microsoft's approach to democratizing AI through Azure AI services."

Common ground:
- Technical leadership and engineering excellence
- AI/ML innovation and practical applications
- Cloud infrastructure and scalable systems

Professional value proposition:
- Your Python and data science expertise could provide insights on developer experience
- Your startup investment interest aligns with Microsoft's venture activities
- Potential collaboration opportunities in AI/ML space

Conversation starters:
- Ask about Microsoft's vision for AI democratization
- Discuss developer experience with Azure AI services
- Share insights from your work in AI/ML at TechCorp
"""
    
    print(example_output)

def demo_integration_flow():
    """Show how this integrates with the WhatsApp workflow."""
    print("\n" + "🔄 INTEGRATION WITH WHATSAPP WORKFLOW")
    print("=" * 70)
    
    flow_steps = [
        "1. User sends WhatsApp message: 'Research John Smith at Microsoft for me'",
        "2. WhatsApp node processes message and generates AI response",
        "3. AI decides to use search_person_and_generate_intro tool",
        "4. Tool searches Perplexity for John Smith's professional info",
        "5. Tool retrieves user's memories for personal context",
        "6. Tool generates personalized introduction strategy",
        "7. Tool stores research results in user's memory",
        "8. AI formats response for WhatsApp and sends back to user",
        "9. User receives comprehensive research and introduction strategy"
    ]
    
    for step in flow_steps:
        print(f"   {step}")
    
    print(f"\n💡 Key Benefits:")
    benefits = [
        "Combines real-time web search with personal context",
        "Automatically stores research for future reference",
        "Provides actionable networking strategies",
        "Works seamlessly within WhatsApp conversation",
        "Personalizes recommendations based on user background"
    ]
    
    for benefit in benefits:
        print(f"   • {benefit}")

def main():
    """Run the demo."""
    print("🚀 PERPLEXITY TOOLS DEMO")
    print("=" * 70)
    print("This demo shows how the Perplexity search tools work")
    print("within the WhatsApp workflow for personalized networking.")
    
    demo_tool_descriptions()
    demo_usage_scenarios()
    demo_expected_output()
    demo_integration_flow()
    
    print("\n" + "✨ CONCLUSION")
    print("=" * 70)
    print("The Perplexity integration provides powerful people and company research")
    print("capabilities that are automatically personalized using the user's memory.")
    print("This enables intelligent networking assistance directly through WhatsApp.")
    
    print(f"\n📋 TO USE WITH REAL API:")
    print("1. Set PERPLEXITY_API_KEY in your .env file")
    print("2. Ensure OPENAI_API_KEY is set for memory operations")
    print("3. Send a WhatsApp message asking to research someone")
    print("4. The AI will automatically use these tools when appropriate")

if __name__ == "__main__":
    main() 