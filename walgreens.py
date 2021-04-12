import asyncio
import time
import json
import yaml
from datetime import datetime
from playwright.async_api import async_playwright

## ASYNC HTTP REQUESTS
# https://www.twilio.com/blog/asynchronous-http-requests-in-python-with-aiohttp
# https://stackoverflow.com/questions/55234194/why-do-i-have-to-use-async-with-when-using-the-aiohttp-module

## GIT BRANCHING
# https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging

# https://playwright.dev/python/docs/selectors/
# https://playwright.dev/python/docs/api/class-page?_highlight=goto#pagefillselector-value-kwargs
# https://playwright.dev/python/docs/api/class-page#pageclickselector-kwargs
# https://docs.python.org/3/library/http.cookiejar.html

async def test_run(playwright, server, user, password):
    walgreens_covid_vaccine_landing_url = 'https://www.walgreens.com/findcare/vaccination/covid-19?ban=covid_vaccine1_landing_schedule'
    firefox = playwright.firefox
    browser = await firefox.launch(headless=False, slow_mo=100)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto(walgreens_covid_vaccine_landing_url, wait_until='networkidle')
    await page.click("text=Schedule new appointment")
    await page.fill("[id='inputLocation']", "30265")
    await page.click("text=Search")

    # cookies = await context.cookies()
    storage = await context.storage_state()
    with open('TEST_LOCAL_STORAGE.json', 'w') as write_file:
        json.dump(storage, write_file)
    
    await browser.close()
    return


async def login(playwright, email, code, security):
    walgreens_login_url = 'https://www.walgreens.com/login.jsp?ru=%2Ffindcare%2Fvaccination%2Fcovid-19%2Feligibility-survey%3Fflow%3Dcovidvaccine%26register%3Drx'
    firefox = playwright.firefox
    browser = await firefox.launch(headless=False, slow_mo=100)
    context = await browser.new_context()
    page = await context.new_page()
    
    await page.goto(walgreens_login_url, wait_until='networkidle')
    
    await asyncio.sleep(2)
    await page.click("input[name=username]")
    
    await asyncio.sleep(0.8)
    await page.fill("input[name=username]", email)
    
    await asyncio.sleep(1.6)
    await page.click("input[name=password]")
    
    await asyncio.sleep(1.2)
    await page.fill("input[name=password]", code)
    
    await asyncio.sleep(3.8)
    await page.click("[aria-label='Sign in']")

    await asyncio.sleep(2)
    await page.wait_for_load_state('load')
    await page.wait_for_load_state('networkidle')
    await page.wait_for_selector("[class='ApptScreens'], #radio-security")

    await asyncio.sleep(2.2)
    await page.check("#radio-security");

    await asyncio.sleep(1.6)
    await page.click("#optionContinue");

    await asyncio.sleep(3)
    await page.fill("#secQues", security);

    await asyncio.sleep(0.7)
    await page.click("#validate_security_answer");

    # await page.wait_for_selector("[class='ApptScreens']")
    await page.wait_for_load_state('networkidle')
    await asyncio.sleep(60)

    storage = await context.storage_state()
    with open('TEST_LOGIN_STORAGE.json', 'w') as write_file:
        json.dump(storage, write_file)

    await browser.close()


async def retrieve_cookies(file):
    async with open(file) as json_file:
        storage = json.load(json_file)

        async for cookie in storage['cookies']:
            if cookie['name'] == 'XSRF-TOKEN':
                xsrf_token = cookie
    
    return storage, xsrf_token


async def main():

    # Read in config info
    info = yaml.safe_load(open('info.yml'))
    email = info['walgreens']['email']
    code = info['walgreens']['code']
    security = info['walgreens']['security']

    async with async_playwright() as playwright:
        return await login(playwright, email, code, security)

asyncio.run(main())
