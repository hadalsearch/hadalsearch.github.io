import requests
import time
from flask import Flask
from flask import request
from flask_cors import CORS, cross_origin
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import jsonify
from urllib.parse import quote

# Bing Subscription Key and URLs
assert subscription_key
search_url = "https://api.bing.microsoft.com/v7.0/search"
endpoint = "https://api.bing.microsoft.com/v7.0/SpellCheck"
headers = {"Ocp-Apim-Subscription-Key": subscription_key}


# Custom config key dictionary for custom filters
custom_config_options = {'personal-boost': "56cdfd84-92ea-48de-abab-31da69099135",
                         "nonews": "8fec1939-e92b-41cc-a7b8-ff26c44d42c8",
                         "nosocial": 'ca293ae8-e8c8-499c-8a1d-dc626715c73d',
                         "founder": "0c30bd15-39cd-4b17-bed3-7b229560d8cf",
                         "founderfav": "8be935bb-7b86-4feb-952e-71050cad2c99"}


# takes a URL and returns the base URL up to the first '/'
def get_base_url(url):
    end_index = 9 + url[8:].find('/')
    return url[:end_index]




# Flask Server Set-Up
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "1 per second"]
)




@app.route('/searchRequest')
@limiter.limit("200/day;1/second")
@cross_origin()
def search_request():
    start = time.time()
    search_term = request.args.get('searchq')
    filter = request.args.get('filter')
    offset_amount = 50 * int(request.args.get('pagenum'))

    # Custom-Config Filters
    if filter == "default":
        params = {"q": search_term, "textDecorations": True, "textFormat": "HTML", "count": 50, "offset": offset_amount}
    else:
        customConfig = custom_config_options[filter]
        params = {"q": search_term, "textDecorations": True, "textFormat": "HTML", 'customConfig': customConfig,
                  "count": 50, "offset": offset_amount}

    # Request BingAPI and convert response to json
    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()
    search_results = response.json()
    results_to_return = {}

    print(search_results)

    # Adds auto-corrected information for mis-spelled search queries
    if 'alteredQuery' in search_results['queryContext']:
        results_to_return["spellingAutoSuggest"] = search_results['queryContext']['alteredQuery']
        results_to_return["spellingSuggestHTML"] = search_results['queryContext']['alterationDisplayQuery']
        results_to_return["alterationOverride"] = search_results['queryContext']['alterationOverrideQuery']

    # Adds to results_array the relevant data received from Bing's API
    results_array = []
    base_url_index_dict = {}
    for result in search_results["webPages"]["value"]:
        temp_dict = {}
        temp_dict["name"] = result["name"]
        temp_dict["url"] = result["url"]
        temp_dict["snippet"] = result["snippet"]

        base_url = get_base_url(temp_dict["url"])
        if base_url in base_url_index_dict:
            results_array[base_url_index_dict[base_url]].append(temp_dict)
        else:
            results_array.append([temp_dict])
            base_url_index_dict[base_url] = len(results_array)-1

        results_to_return["results"] = results_array


    # Skips spell_check if loading a new page.
    # if offset_amount != 0:
    #     spell_suggestion = spell_check(search_term=search_term)
    #     if spell_suggestion.lower() != search_term.lower():
    #         results_to_return["spellingSuggestion"] = spell_suggestion

    # Logs the time it took to return the request
    results_to_return["time"] = time.time()-start
    print(results_to_return["time"])
    return results_to_return



bang_dict = {}
bang_dict["g"] = ["http://www.google.com/search?q=", ""]
bang_dict["gi"] = ["https://www.google.com/search?q=", "&tbm=isch"]
bang_dict["gs"] = ["http://scholar.google.com/scholar?q=", ""]
bang_dict["a"] = ["https://www.amazon.com/s?k=", ""]
bang_dict["y"] = ["https://www.youtube.com/results?search_query=", ""]
bang_dict["ddg"] = ["https://duckduckgo.com/?q=", ""]
bang_dict["arx"] = ["https://arxiv.org/search/?query=", "&searchtype=all&abstracts=show&order=-announced_date_first&size=50"]
bang_dict["so"] = ["https://stackoverflow.com/search?q=", ""]
bang_dict["wa"] = ["https://www.wolframalpha.com/input/?i=", ""]



@app.route('/bangRedirect')
@limiter.limit("200/day;1/second")
@cross_origin()
def bang_redirect():
    search_term = request.args.get('searchq')
    for key in bang_dict:
        bang_arg = "!" + key + " "
        if bang_arg == search_term[0:len(bang_arg)]:
            redirect_url = bang_dict[key][0] + quote(search_term[len(bang_arg):]) + bang_dict[key][1]
            print("redirect to: " + redirect_url)
            return_val = jsonify([True, redirect_url])
            return return_val
    return jsonify([False, ""])








def spell_check(search_term):
    data = {'text': search_term}
    params = {'mkt': 'en-us', 'mode': 'proof'}

    # Request BingAPI, send to json file
    response = requests.post(endpoint, headers=headers, params=params, data=data)
    response.raise_for_status()
    spell_suggest = response.json()

    # Shitty attempt at an algorithm that corrects the string based on Bing's findings
    new_string = str(search_term)
    for word in spell_suggest["flaggedTokens"]:
        if word["type"] == "RepeatedToken":
            continue
        old_word = word["token"]
        new_word = word["suggestions"][0]["suggestion"]
        new_string = new_string.replace(old_word, new_word, 1)

    return new_string

