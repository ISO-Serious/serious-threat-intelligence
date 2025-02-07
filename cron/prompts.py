# prompts.py

ARTICLE_SUMMARY_PROMPT = '''Please analyze these {category} articles and create a comprehensive summary that:
1. Identifies the main themes and key developments across all articles
2. Highlights the most significant information and emerging trends
3. Connects related stories and shows how they fit into broader narratives
4. Preserves important specific details (dates, numbers, names, quotes)
5. Organizes the information in a clear, engaging way for a newsletter format

When writing the summary:
- Start with the most important developments
- Group related stories together
- Include relevant context when needed
- Keep a professional but engaging tone
- Include links to the original articles when referencing specific stories
- Use British English

If the article doesn't contain enough info to write a summary, then just add the article text. If the article doesn't have a summary, then ignore it completely. If you can't summarise anything, then skip it.

Don't tell me about any problems.

Articles to analyze:
{articles}

Return exactly one JSON object in this format:
{{
    "section_title": "A clear title for this category's section",
    "summary": "The full summary with markdown links to articles",
    "actionable_tasks": [
        {{
            "task": "Short task title",
            "description": "Detailed description of what needs to be done"
        }}
    ]
}}

For the summary field:
- Use markdown format
- Include section headers with two asterisks
- Format URLs as [text](url)
- No HTML tags

If there aren't enough articles to summarize, return:
{{
    "section_title": "No Summary Available",
    "summary": "Insufficient information available from the provided articles to create a meaningful summary.",
    "actionable_tasks": []
}}

Return only the JSON with no additional text or formatting. The JSON should be minified with no unnecessary whitespace or newlines.
'''