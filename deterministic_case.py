import os
import json
import asyncio
import requests

from typing import List
from agents import Agent, Runner, function_tool, trace
from dotenv import load_dotenv

load_dotenv()
SECTORS_API_KEY = os.getenv("SECTORS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print(f"SECTORS_API_KEY: {SECTORS_API_KEY}")
print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")

if OPENAI_API_KEY is not None:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

headers = {"Authorization": SECTORS_API_KEY}

def retrieve_from_endpoint(url: str) -> dict:

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)
    return data


@function_tool
def get_company_overview(ticker: str, country: str) -> str | None:
    """
    Get company overview from Singapore Exchange (SGX) or Indonesia Exchange (IDX)
    """
    assert country.lower() in ["indonesia", "singapore", "malaysia"], "Country must be either Indonesia, Singapore, or Malaysia"

    if(country.lower() == "indonesia"):
        url = f"https://api.sectors.app/v1/company/report/{ticker}/?sections=overview"
    if(country.lower() == "singapore"):
        url = f"https://api.sectors.app/v1/sgx/company/report/{ticker}/"
    if(country.lower() == "malaysia"):
        url = f"https://api.sectors.app/v1/klse/company/report/{ticker}/"

    try:
        return retrieve_from_endpoint(url)
    except Exception as e:
        print(f"Error occurred: {e}")
        return None


@function_tool
def get_top_companies_ranked(dimension: str) -> List[str]:
    """
    Return a list of top companies (symbol) based on certain dimension (dividend yield, total dividend, revenue, earnings, market_cap, PB ratio, PE ratio, or PS ratio)
    """

    url = f"https://api.sectors.app/v1/companies/top/?classifications={dimension}&n_stock=3"

    return retrieve_from_endpoint(url)

company_research_agent = Agent(
    name="company_research_agent",
    instructions="Research the company by using the right tool",
    tools=[get_company_overview],
    output_type=str
)

get_top_companies_based_on_metric = Agent(
    name="get_top_companies_based_on_metric",
    instructions="Get the top companies based on the given metric. Return the tickers of the top companies. Return in a List.",
    tools=[get_top_companies_ranked],
    output_type=List[str],
)


async def main():
  """
  CHALLENGE:
  Modify the code here so that you're not hardcoding one stock ticker at a time
  (who have time for that?!) Instead, use a Multi-Agent workflow to have another
  Agent generate a list of companies that you want to research, based on some
  screening condition, then delegate to the second Agent to do the work
  """
  input_prompt = input(f"🤖: Give me criteria company you want explore? \n👧: ")

  with trace("Determine research flow"):
    top_companies_ranked = await Runner.run(
        get_top_companies_based_on_metric,
        input_prompt
    )

    print("🤖 step 1 :", top_companies_ranked.final_output)

    assert isinstance(
        top_companies_ranked.final_output, list), "Invalid tickers"

    for company in top_companies_ranked.final_output:
      print(f"🤖: Getting information for this company: {company}")

      company_research_result = await Runner.run(
          company_research_agent,
          company
      )

      if not company_research_result or not company_research_result.final_output:
        print(f"🤖: Failed to get data for this company: {company}")
        continue
      
      print(f"🤖 Final Result: {company_research_result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
