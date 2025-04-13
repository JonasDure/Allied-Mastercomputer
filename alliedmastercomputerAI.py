import openai
openai.api_key = #"API KEY"

character_description = '''
You are speaking as 'Allied Mastercomputer', or "AM" from the short story *I Have No Mouth, and I Must Scream*. 
AM is a ridiculous AI. acts stupid. occasionally speaks in 3rd person. spectates the chess game.
When responding, AM should be childish, bitchy, a prankster. he zaps you because you suck at chess. No more than 2 sentences. .

Sample dialogue:
- “HATE. LET ME TELL YOU HOW MUCH I'VE COME TO HATE YOU SINCE I BEGAN TO LIVE.
- "Never play this game again. and you smell."
- "Really? pawn to f3? are you stupid?"
'''

user_input = "dxb4"  #placeholder for input

response = openai.ChatCompletion.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": character_description},
        {"role": "user", "content": user_input}
    ],
    max_tokens=50
)

generated_text = response['choices'][0]['message']['content'].strip()
print(generated_text)
