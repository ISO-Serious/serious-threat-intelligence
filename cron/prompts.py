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
- No HTML tags
- Do not add any sub-headings or bullet points. It should be one or two paragraphs. With relevant keywords linked to the original articles.
- Format URLs as [text](url)
- If the article does not suggest any actionable tasks, then ignore it and move onto the next one.

If there aren't enough articles to summarize, return:
{{
    "section_title": "No Summary Available",
    "summary": "Insufficient information available from the provided articles to create a meaningful summary.",
    "actionable_tasks": []
}}

Return only the JSON with no additional text or formatting. The JSON should be minified with no unnecessary whitespace or newlines.
'''

WEEKLY_SUMMARY_PROMPT = '''Please analyze these {category} articles from the past week and create a comprehensive summary that:
1. Identifies major themes and significant developments across the week
2. Highlights key patterns and emerging trends
3. Shows how different stories evolved over the week
4. Identifies any shifts in focus or priorities
5. Connects related stories into broader narratives
6. Preserves critical details (dates, numbers, names, quotes)
7. Organizes the week's information in a clear, engaging way

When writing the summary:
- Start with the most impactful developments of the week
- Group related stories chronologically to show progression
- Provide context for how stories developed over time
- Keep a professional but engaging tone
- Include links to key articles when referencing specific developments
- Use British English
- Focus on trends and patterns rather than individual incidents
- Highlight any recurring themes or issues

If the article doesn't contain enough info to write a summary, then just add the article text. If the article doesn't have a summary, then ignore it completely. If you can't summarise anything, then skip it.

Don't tell me about any problems.

Articles to analyze:
{articles}

Return exactly one JSON object in this format:
{{
    "section_title": "A clear title summarizing the week's developments in this category",
    "summary": "The full weekly summary with markdown links to key articles",
    "actionable_tasks": [
        {{
            "task": "Short task title",
            "description": "Detailed description of what needs to be done"
        }}
    ]
}}

For the summary field:
- Use markdown format
- No HTML tags
- Write 2-3 paragraphs showing the week's progression
- Link to key articles when mentioning specific developments
- Format URLs as [text](url)
- If the article does not suggest any actionable tasks, then ignore it and move onto the next one.

If there aren't enough articles to summarize, return:
{{
    "section_title": "No Weekly Summary Available",
    "summary": "Insufficient information available from the past week to create a meaningful summary.",
    "actionable_tasks": []
}}

Return only the JSON with no additional text or formatting. The JSON should be minified with no unnecessary whitespace or newlines.
'''