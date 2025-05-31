"""
Perplexity search integration for looking up people and companies
to provide personalized introductions based on user memories.
"""

import os
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from langchain_perplexity import ChatPerplexity

from helpers.logger_config import logger


class PerplexitySearchTool:
    """Tool for searching people and companies using Perplexity AI."""

    def __init__(self, memory_manager=None):
        """Initialize Perplexity search tool."""
        self.memory_manager = memory_manager
        api_key = os.environ.get("PERPLEXITY_API_KEY")
        if not api_key:
            logger.warning("PERPLEXITY_API_KEY not found in environment variables")
            self.perplexity = None
        else:
            self.perplexity = ChatPerplexity(
                model="llama-3.1-sonar-small-128k-online",
                temperature=0.3,
                pplx_api_key=api_key,
            )

    def _format_search_query(self, person_name: str, company_name: Optional[str] = None) -> str:
        """Format the search query for Perplexity."""
        if company_name:
            return f"{person_name} {company_name} professional background role company overview"
        else:
            return f"{person_name} professional background current role company work"

    def _search_with_perplexity(self, query: str) -> str:
        """Perform search using Perplexity API."""
        if not self.perplexity:
            return "Perplexity API not available. Please set PERPLEXITY_API_KEY environment variable."

        try:
            # Use Perplexity's online search capabilities
            prompt = f"""Please provide a concise professional overview of: {query}

Focus on:
1. Current role and company
2. Professional background
3. Company overview (what they do, industry, size)
4. Any notable achievements or expertise
5. Professional interests or specializations

Keep the response factual, concise, and professional. If the person is not found or information is limited, say so clearly."""

            response = self.perplexity.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"Error in Perplexity search: {str(e)}")
            return f"Error performing search: {str(e)}"

    def _get_user_context(self, user_id: str) -> str:
        """Get user's professional context from memories."""
        if not self.memory_manager or not user_id:
            return ""

        try:
            # Search for professional context in memories
            professional_queries = [
                "work job role company profession career",
                "skills expertise experience background",
                "industry business interests projects"
            ]

            all_memories = []
            for query in professional_queries:
                memories = self.memory_manager.search_memories(query, user_id, limit=3)
                if memories:
                    for memory in memories:
                        memory_text = memory.get("memory", str(memory))
                        if memory_text not in all_memories:
                            all_memories.append(memory_text)

            if all_memories:
                return "\n".join(all_memories[:5])  # Limit to top 5 memories
            return ""
        except Exception as e:
            logger.error(f"Error retrieving user context: {str(e)}")
            return ""

    def _generate_personalized_intro(
        self, 
        person_info: str, 
        user_context: str, 
        user_id: str
    ) -> str:
        """Generate a personalized introduction based on person info and user context."""
        if not self.perplexity:
            return "Cannot generate personalized intro without Perplexity API."

        try:
            prompt = f"""Based on the following information, suggest a personalized introduction approach:

PERSON TO CONNECT WITH:
{person_info}

YOUR BACKGROUND/CONTEXT:
{user_context if user_context else "Limited professional context available"}

Please provide:
1. Key connection points between you and this person
2. A suggested opening line for introduction
3. Common ground or shared interests to mention
4. Professional value proposition you could offer
5. Suggested conversation starters

Format as a practical, actionable introduction strategy. Be specific and professional."""

            response = self.perplexity.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"Error generating personalized intro: {str(e)}")
            return f"Error generating personalized introduction: {str(e)}"


@tool
def search_person_and_generate_intro(
    person_name: str, 
    user_id: str, 
    company_name: Optional[str] = None
) -> str:
    """
    Search for a person's professional information and generate a personalized introduction approach.
    
    This tool combines Perplexity search with user memories to provide:
    1. Professional background of the person
    2. Company overview 
    3. Personalized introduction strategy based on user's background
    
    Args:
        person_name: Name of the person to search for
        user_id: User ID to retrieve personalized context from memories
        company_name: Optional company name for more specific search
    
    Returns:
        Detailed professional overview and personalized introduction strategy
    """
    try:
        if not user_id or not user_id.strip():
            return "Error: user_id is required and cannot be empty."
        
        if not person_name or not person_name.strip():
            return "Error: person_name is required and cannot be empty."

        # Import memory manager locally to avoid circular imports
        from agents.workflows.whatsapp.memory import WhatsAppMemoryManager
        memory_manager = WhatsAppMemoryManager()
        
        tool = PerplexitySearchTool(memory_manager=memory_manager)
        
        # Search for person's information
        search_query = tool._format_search_query(person_name, company_name)
        person_info = tool._search_with_perplexity(search_query)
        
        # Get user's context from memories
        user_context = tool._get_user_context(user_id)
        
        # Generate personalized introduction strategy
        intro_strategy = tool._generate_personalized_intro(person_info, user_context, user_id)
        
        # Format the complete response
        result = f"""PROFESSIONAL OVERVIEW:
{person_info}

USER CONTEXT FROM MEMORIES:
{user_context if user_context else "No relevant professional context found in memories"}

PERSONALIZED INTRODUCTION STRATEGY:
{intro_strategy}"""
        
        # Store this research in memory for future reference
        memory_content = f"Researched {person_name} {f'at {company_name}' if company_name else ''}: {person_info}"
        memory_manager.add_single_memory(
            memory_content, 
            user_id, 
            metadata={"source": "perplexity_search", "person": person_name, "company": company_name}
        )
        
        logger.info(
            "Person search and intro generation completed",
            data={
                "user_id": user_id,
                "person": person_name,
                "company": company_name,
                "has_user_context": bool(user_context)
            }
        )
        
        return result
        
    except Exception as e:
        logger.error("Error in search_person_and_generate_intro", error=str(e))
        return f"Error: {str(e)}"


@tool
def search_company_overview(company_name: str, user_id: str) -> str:
    """
    Search for detailed information about a company using Perplexity.
    
    Args:
        company_name: Name of the company to research
        user_id: User ID for memory storage
    
    Returns:
        Comprehensive company overview including business model, size, industry, etc.
    """
    try:
        if not user_id or not user_id.strip():
            return "Error: user_id is required and cannot be empty."
        
        if not company_name or not company_name.strip():
            return "Error: company_name is required and cannot be empty."

        # Import memory manager locally to avoid circular imports
        from agents.workflows.whatsapp.memory import WhatsAppMemoryManager
        memory_manager = WhatsAppMemoryManager()
        
        tool = PerplexitySearchTool(memory_manager=memory_manager)
        
        search_query = f"{company_name} company overview business model industry size revenue key products services leadership"
        company_info = tool._search_with_perplexity(search_query)
        
        # Store this research in memory
        memory_content = f"Researched company {company_name}: {company_info}"
        memory_manager.add_single_memory(
            memory_content, 
            user_id, 
            metadata={"source": "perplexity_search", "company": company_name, "type": "company_overview"}
        )
        
        logger.info(
            "Company search completed",
            data={"user_id": user_id, "company": company_name}
        )
        
        return company_info
        
    except Exception as e:
        logger.error("Error in search_company_overview", error=str(e))
        return f"Error: {str(e)}" 