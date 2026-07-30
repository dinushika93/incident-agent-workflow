
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv
import asyncio

load_dotenv()


class inputModel(BaseModel):
   number: int = Field(description="The lucky number")
   user: str | None = Field(default=None, description="name of the user")

roulette_agent = Agent(  
  'openai:gpt-5.2',
  deps_type=inputModel,
  output_type=str,
  system_prompt=(
      'Use the `roulette_wheel` function to see if the user has won based on the number they provide.'
      'Inform the user with a relevent message based on the output'
  ),
)
@roulette_agent.tool
async def roulette_wheel(ctx: RunContext[inputModel], square: int) -> str:
  """check if the square is a winner"""
  return 'winner' if square == ctx.deps.number else 'loser'

@roulette_agent.system_prompt
async def get_customer_name(ctx: RunContext[inputModel]):
  """add the customer name to the system prompt"""
  if ctx.deps.user:
        return f"The user's name is {ctx.deps.user}. adedress them by thir name"
  else:
      return f"The user is unknown address them politely in your reponse"


async def main():
  # Run the agent
    deps  = inputModel(
    number=17
    )
    result = await roulette_agent.run('Put my money on square eighteen', deps=deps)
    print(result.output)
#> True


if __name__ == "__main__":
    asyncio.run(main())