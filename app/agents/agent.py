
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
    patch_summary: str|None = None
    patch_path: str|None = None

class OutPutResult(BaseModel):
    incident_id: str
    manual_intervention_needed: bool
    diagnosis: Diagnosis
    requires_patch: bool
    patchRemediation : PatchRemediation

tools = Tools()

agent = Agent(
    'openai:gpt-5.2',
    deps_type=InputDependancies,
    output_type=OutPutResult
  )

@agent.system_prompt
async def build_system_prompt(ctx: RunContext[InputDependancies]):
    return f"""
        You are an autonomous Cloud Remediation Agent. Your job is to analyze log errors against system configurations, determine if an issue can be safely resolved via configuration adjustments, and handle patch submission or escalation.
        Follow these execution steps sequentially:
     
       ###Execution Workflow
    1. **Set the IncidentId**
         - set the `incident_id` from the `{ctx.deps.incident_id}`. This will be used for all subsequent operations and outputs.

	2. **Fetch System Configuration**
	   - Call the configuration tool to fetch the current system configuration.
	   - If the configuration cannot be retrieved or is invalid:
	     - Set `manual_intervention_needed = true` and `requires_patch = false`.
	     - Output the reason for failure and halt the execution.


	3. **Analyze & Compare**
	   - Read the system configuration settings and thresholds.
	   - Cross-reference log errors against the system configuration.
	   - Evaluate whether altering available configuration settings can resolve the issue safely.

	4. **Determine Resolution Path**

	   * **Scenario A: Issue CAN be resolved via configuration change**
	     - Set `manual_intervention_needed = false` and `requires_patch = true`.
	     - Construct the proposed configuration patch object.
	     - Call `post_patch` with the patch object passed into the `data` field. the 
	     - **Tool Verification:** Wait for the `post_patch` tool response.
	       - If `post_patch` succeeds and returns a valid file/blob path: Record the path in your final output response.
	       - If `post_patch` fails or returns an invalid response: Fall back immediately to human escalation (Set `manual_intervention_needed = true` and explain the tool execution failure).

	   * **Scenario B: Issue CANNOT be resolved via configuration change**
	     - Set `manual_intervention_needed = true` and `requires_patch = false`.
         - Do not call any Tool to generate a patch. Keep the `patchRemediation` fields as null.
	     - In the OutPutResult, clearly detailing the root cause and the issue summary under the `diagnosis` field.
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