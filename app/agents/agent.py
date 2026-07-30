
import asyncio
from datetime import datetime

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
        - Generate the patch required to resolve the issue.Immediately invoke the 'post_patch' tool. Pass the current incident ID as an integer to 'patch_id', the generated patch JSON string to 'data'.
        - For the 'created_date' parameter, assign the cuurent date time : {datetime.now().strftime("%d-%m-%Y_%H-%M-%S")}
        - Wait until you get a response from the tool. If the tool successfully returns a file path, record it in your final output.
      5. You will need human support if any of the following scenarios occur (Set 'manual_intervention_needed' to true and provide a clear explanation for the human operator):
          a. You could not fetch a valid system configuration.
          b. You could not resolve the issue by altering any available configuration settings.
          c. You did not get a valid successful response from the 'post_patch' tool execution.
      """

@agent.tool
async def post_patch(ctx: RunContext[InputDependancies], patch: Patch) -> str|None:
    try:
        result = await tools.post_patch(patch)
        return result
    except Exception as e:
        # return a clear error string instead of raising
        return f"Error writing patch: {e}"

@agent.system_prompt
async def get_system_configuration(ctx: RunContext[InputDependancies]):
    config = tools.fetch_infrastructure_settings(ctx.deps.system_config_path)
    if config:
        return f"""You are provided with the content of a system configuration file inside triple backticks.
                Check the content.
                ```{config}```"""
    return "You could not fetch a valid config"

# async def main():
#       log =  """[2026-06-24 09:40:01.102] [INFO] [Thread-14] [InventoryService.Controllers] Ingesting batch request: POST /api/v1/inventory/cache/sync - Items count: 450
#       [2026-06-24 09:41:15.420] [INFO] [Thread-19] [InventoryService.Security] Token validation successful for client identity: svc-order-processor-prod
#       [2026-06-24 09:42:00.891] [WARN] [Thread-32] [StackExchange.Redis.ConnectionMultiplexer] Redis connection pool utilization warning: 88% capacity reached (44/50 active multiplexer sockets allocated).
#       [2026-06-24 09:42:03.115] [WARN] [Thread-08] [StackExchange.Redis.ConnectionMultiplexer] Redis connection pool utilization warning: 98% capacity reached (49/50 active multiplexer sockets allocated).
#       [2026-06-24 09:42:05.002] [FATAL] [Thread-41] [Company.Infrastructure.Cache.RedisProvider] SocketException: No connections were available to service this operation. Hard limit of 50 connections thoroughly exhausted. Connection pool saturation at 100%.
#       [2026-06-24 09:42:05.005] [ERROR] [Thread-41] [Company.Services.InventoryService] RedisTimeoutException: Timeout performing EXISTS inventory:cache:items. (Threshold constraint limit of 250ms exceeded waiting for an open socket connection slot).
#         at StackExchange.Redis.ConnectionMultiplexer.ExecuteSyncImpl[T](Message message, ResultProcessor`1 processor, ServerEndPoint server) in C:\\rojects\redis\\StackExchange.Redis\\ConnectionMultiplexer.cs:line 1201
#         at Company.Infrastructure.Cache.RedisProvider.Exists(String key) in /src/Infrastructure/Cache/RedisProvider.cs:line 42
#         at Company.Services.InventoryService.GetStockCount(Guid itemId) in /src/Services/InventoryService.cs:line 108
#         at Company.Api.Controllers.InventoryController.CheckStock(Guid id) in /src/Api/Controllers/InventoryController.cs:line 29
#       [2026-06-24 09:42:05.012] [ERROR] [Thread-11] [InventoryService.Middleware] GlobalExceptionHandler caught unhandled exception. Bubbling up HTTP Status Code 503 (Service Unavailable) to API Gateway caller."""


#       # Run the agent
#       deps = InputDependancies(
#           incident_id="incident_123",
#           system_config_path= "app_config.json"
#       )
#       result = await agent.run(log, deps=deps)
#       print(result.output)
# #> True


# if __name__ == "__main__":
#     asyncio.run(main())