# Google_search_scraper
Scrapes links from Google search pages 


This is a Google Search scraper. I needed news dataset for any query (category) possible 
so I ended up scraping google's results using Selenium. 
If you have any questions or ideas you are welcome to write me: __khrvanya@gmail.com__


To start with, if you just need english news dataset on specific topic you may run:
scrape_query_news_articles(list_of_queries, list_of_links_number_for_queries)
and have directory 'queries' in the same dir with .py file. After ending
there would be a dir in the 'queries' with your dataset (.txt files)
If there are problems with requirements, look in the code
Also change 420 line to run_chromedriver() 
However you'll have problems with recaptcha if you parse > ~300 links (read below)

If you want to scape other google search stuff consider my 
scrape_query_news_articles() function. You can change it a bit and scrape 
text from other google search categories (news, videos, all) from different 
countries on diffrent languages. 
If you want to scrape videos or photos from google, you may
consider some of the structures or functions


scrape_query_news_articles() parametrs:

list_of_queries: is a list of strings which would be googled, like:
['flowers', 'many roses', 'love'] or ['peace'] == 'peace'

list_of_links_number_for_queries: is a list of integers%10 = 0
each int is for query in the first list and stands for the number 
of first links that would be parsed from the gsearch, like:
[100, 150, 30] or [100, 100, 100] == 100
		
Examples:
scrape_query_news_articles(['flowers', 'roses'], [200, 100])
scrape_query_news_articles(['flowers', 'feelings'], 100)   or the same
scrape_query_news_articles(['flowers', 'feelings'], [100, 100])

You could also run it from terminal, printing:
scrape_query_news_articles(argv[1].split(', '), 
									[int(c) for c in argv[2].split(', ')])
where arguments are the same just given as 
'query_1, query_2' and 'number_q1, number_q2' 

Examples:
python scrape_queries.py 'flowers, feelings' '100'     or the same
python scrape_queries.py 'flowers, feelings' '100, 100'



Now lets get deeper in some details:

Google search limitation:
Each query in Google search has ~350 links results
Therefore, if you want to make a normal query category, you need to make 
a few queries. Thats why I've made a query list.
(all repeats of these queries are managed)

Recaptcha:
If you want to scrape a lot of articles, like:
scrape_query_news_articles(['rose', 'roses', 'flowers', 'feelings', 'love'], 300)
Google would consider you to be a robot ~3 times, so you need to solve
recaptcha somehow. I tried, but it fucked me. So I found some automated stuff
where people solve captchas remotely for you. It costs ~2.2$ for 1000 recaptchas
First of all go there https://antcpt.com/eng/information/recaptcha-2-selenium.html
and download browzer plagin then go there anti-captcha.com register, pay some money
and you will get two global constants:
ANTICAPTCHA_PLUGIN_PATH = os.path.join(CURR_PATH, 'anticaptcha-plugin_v0.50.crx')
ANTICAPTCHA_API_KEY = "00000000000your0key0000000000000"

Some global constants:
SCRAPED_LANGUAGE = 'en'      
MIN_SCRAPED_SIZE = .35        (kb)
CURR_PATH = os.path.abspath(os.curdir)
QUERIES_PATH = os.path.join(CURR_PATH, 'queries')

Why there are less articles scrapes than links scraped:
Scrape wasn't dumped if:
google search has less results than you needed
google search has links repeats of other queries  
scraped language is wrong
scraped size is wrong

P.S. There would be a lot of warnings but don't mind them)




