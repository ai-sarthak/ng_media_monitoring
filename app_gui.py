import praw
import pandas as pd
import requests
import json
import streamlit as st

# Sidebar for selecting between Reddit and HackerNews
scraping_choice = st.sidebar.radio("Select Scraping Source", ["Reddit Scraping", "HackerNews Scraping"])

# Initialize lists and placeholders for the keywords
keywords_input = st.text_input("Enter keywords (comma-separated)", value="customer service automation, GenAI in contact center, customer service, generative ai")

# Default empty lists for posts and news data
posts = []
final_news_data = []

# Conditional input fields based on radio button selection
if scraping_choice == "Reddit Scraping":
    # Sidebar inputs for Reddit credentials
    client_id = st.sidebar.text_input("Client ID", type="password")
    client_secret = st.sidebar.text_input("Client Secret", type="password")
    user_agent = st.sidebar.text_input("User Agent", type="password")

    # Button to start the Reddit scraping process
    run_button_reddit = st.button("Run Reddit Scraping")

    if run_button_reddit:
        if not client_id or not client_secret or not user_agent:
            st.error("Please fill in all the required fields in the sidebar for Reddit Scraping!")
        else:
            # Initialize Reddit API
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )

            # Convert keywords input to list
            keywords = []
            for keyword in keywords_input.split(","):
                keywords.append(keyword)
            print(keywords)

            

            def search_subreddits(keywords):
                """Search for subreddits that match the given keywords."""
                subreddit_list = set()
                for keyword in keywords:
                    for submission in reddit.subreddit('all').search(keyword, sort='new', time_filter='hour', limit=10):
                        subreddit_list.add(submission.subreddit.display_name)
                return list(subreddit_list)

            def is_valid_subreddit(subreddit):
                """Check if a subreddit exists and is public."""
                try:
                    subreddit_instance = reddit.subreddit(subreddit)
                    return not subreddit_instance.over18 and subreddit_instance.display_name is not None
                except Exception:
                    return False

            def scrape_subreddit(subreddit):
                """Scrape posts and comments from a valid subreddit."""
                try:
                    for submission in reddit.subreddit(subreddit).new(limit=5):
                        submission.comments.replace_more(limit=0)
                        for comment in submission.comments.list():
                            posts.append({
                                'title': submission.title,
                                'url': submission.url,
                                'score': submission.score,
                                'created': submission.created_utc,
                                'subreddit': subreddit,
                                'submission_content': submission.selftext,
                                'comment': comment.body,
                                'comment_author': comment.author.name if comment.author else "Unknown"
                            })
                except Exception as e:
                    st.warning(f"Error scraping {subreddit}: {e}")

            # Search for relevant subreddits based on keywords
            found_subreddits = search_subreddits(keywords)
            valid_subreddits = [subreddit for subreddit in found_subreddits if is_valid_subreddit(subreddit)]

            if valid_subreddits:
                st.write(f"Found {len(valid_subreddits)} valid subreddits for scraping.")
                
                # Scrape posts and comments from valid subreddits
                for subreddit in valid_subreddits:
                    scrape_subreddit(subreddit)

                if posts:
                    # Convert to DataFrame
                    reddit_df = pd.DataFrame(posts)
                    st.write(f"Scraped {len(posts)} posts and comments.")
                    st.dataframe(reddit_df)

                    # Save the results to an Excel file
                    output_file_reddit = 'reddit_posts_relevant.xlsx'
                    reddit_df.to_excel(output_file_reddit, index=False)
                    st.success(f"Data saved to {output_file_reddit}.")

                    # Provide a download button for the Excel file
                    with st.sidebar:
                        st.download_button(
                            label="Download Excel File",
                            data=open(output_file_reddit, "rb").read(),
                            file_name=output_file_reddit,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.warning("No relevant posts found in valid subreddits.")
            else:
                st.warning("No valid subreddits found for the given keywords.")

elif scraping_choice == "HackerNews Scraping":
    # No need for credentials, just the keyword input
    run_button_hn = st.button("Run HackerNews Scraping")

    if run_button_hn:
        keywords = []
        for keyword in keywords_input.split(","):
            keywords.append(keyword)
        print(keywords)

        # Function to extract the required fields from each item in the HackerNews API response
        def extract_news_data(data):
            news_data = []
            try:
                for item in data['hits']:
                    title = item.get('title', 'No Title Available')
                    story_date = item.get('created_at', 'No Date Available')
                    author = item.get('author', 'Unknown Author')
                    url = item.get('url', 'No URL Available')

                    matched_keywords = item.get('_highlightResult', {}).get('title', {}).get('matchedWords', [])
                    news_text = item.get('_highlightResult', {}).get('title', {}).get('value', '').replace("<em>", "").replace("</em>", "")

                    news_data.append({
                        "News Title": title,
                        "News Text": news_text,
                        "Story Date": story_date,
                        "Matched Keywords": ", ".join(matched_keywords),
                        "URL": url,
                        "Author Name": author
                    })
            except KeyError as e:
                print(f"KeyError: {e}")
            return news_data

        # Collect data from the HackerNews API for each keyword
        for keyword in keywords:
            url = f"https://hn.algolia.com/api/v1/search?query={keyword}"
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                final_news_data.extend(extract_news_data(data))
            else:
                print(f"Failed to fetch data for keyword: {keyword}")

        if final_news_data:
            # Convert the list of dictionaries to a DataFrame
            hn_df = pd.DataFrame(final_news_data)

            # Save the DataFrame to a CSV file
            output_file_hn = "hacker_news_search_results.csv"
            hn_df.to_csv(output_file_hn, index=False)
            st.success(f"Data has been saved to {output_file_hn}")

            # Provide a download button for the CSV file
            with st.sidebar:
                st.download_button(
                    label="Download CSV File",
                    data=open(output_file_hn, "rb").read(),
                    file_name=output_file_hn,
                    mime="text/csv"
                )

        else:
            st.warning("No relevant news found for the given keywords.")
