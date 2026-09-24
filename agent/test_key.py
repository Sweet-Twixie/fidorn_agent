from dotenv import load_dotenv
import anthropic

load_dotenv()
client = anthropic.Anthropic()
msg = client.messages.create(model="claude-sonnet-5", max_tokens=50,
                             messages=[{"role": "user", "content": "Say hi"}])
print(msg.content[0].text)