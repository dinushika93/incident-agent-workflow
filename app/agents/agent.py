
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from ..dependancies.tools import Patch, Tools

load_dotenv()

class InputDependancies(BaseModel):
    incident_id: str
    system_config_path: str


class Diagnosis(BaseModel):
    summary: str
    root_cause: str

class PatchRemediation(BaseModel):
    requires_patch: bool
    patch_summary: str|None = None
    patch_path: str|None = None

class OutPutResult(BaseModel):
    incident_id: str
    manual_intervention_needed: bool
    diagnosis: Diagnosis
    patchRemediation : PatchRemediation

tools = Tools()

agent = Agent(
    'openai:gpt-5.2',
    deps_type=InputDependancies,
    output_type=OutPutResult
  )

@agent.system_prompt
async def build_system_prompt(ctx: RunContext[InputDependancies]):
      incident_id = ctx.deps.incident_id
      return f"""You are a system admin. Your task is to resolve an issue by analyzing the log content provided for incident {incident_id}.

      Follow the steps below:
      1. Fetch the system configuration using the correct tool.
      2. Read the configuration.
      3. Compare the log errors against the system thresholds. Check whether you can resolve the issue by altering the configuration settings.
      4. If you can resolve the issue:
        - You do not need human support. Set 'requires_patch' to true and 'manual_intervention_needed' to false.
        - Generate the patch changes and pass them as an object in the 'data' field to 'post_patch'.
        - The application supplies the incident ID, filename, and creation timestamp. Do not generate those fields.
        - Wait until you get a response from the tool. If the tool successfully returns a file path, record it in your final output.
      5. You will need human support if any of the following scenarios occur (Set 'manual_intervention_needed' to true and provide a clear explanation for the human operator):
          a. You could not fetch a valid system configuration.
          b. You could not resolve the issue by altering any available configuration settings.
          c. You did not get a valid successful response from the 'post_patch' tool execution.
      """

@agent.tool
async def post_patch(ctx: RunContext[InputDependancies], patch: Patch) -> str|None:
    try:
        result = await tools.post_patch(ctx.deps.incident_id, patch)
        return result
    except Exception as e:
        # return a clear error string instead of raising
        return f"Error writing patch: {e}"

@agent.system_prompt
async def get_system_configuration(ctx: RunContext[InputDependancies]):
    config = await tools.fetch_infrastructure_settings(ctx.deps.system_config_path)
    if config:
        return f"""You are provided with the content of a system configuration file inside triple backticks.
                Check the content.
                ```{config}```"""
    return "You could not fetch a valid config"