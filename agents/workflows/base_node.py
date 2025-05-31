from langchain_openai import OpenAIEmbeddings

from agents.constants.tenant_maps import OPENAI_API_KEY
from agents.utils.langchain_wrapper import LangChainWrapper


class BaseNode:
    def __init__(
        self,
        workflow_name: str,
    ):
        """
        Base class for all workflow node classes.

        Args:
            workflow_name (str): The name of the workflow
        """
        self.workflow_name = workflow_name
        self.openai_api_key = OPENAI_API_KEY
        self.llm = LangChainWrapper(
            workflow_name=workflow_name,
        )
        self.embedding_model = None

    def initialize_embedding_model(self, model_name="text-embedding-3-small"):
        """
        Initialize the embedding model. Call this method when needed instead of
        initializing in the constructor to avoid unnecessary initialization.

        Args:
            model_name (str): The name of the embedding model to use
        """
        self.embedding_model = OpenAIEmbeddings(
            api_key=self.openai_api_key, model=model_name
        )

    # These are all the common nodes that will be used across workflows
    def end_node(self, state):
        """Common end node that marks a workflow as finished"""
        return {"finished": True}

    def is_workflow_finished(self, state):
        """Check if the workflow is finished"""
        return state.get("finished", False)
