OpenAI Compatibility Endpoints | LM Studio 

 LM Studio 
 LM Studio 
 Search ⌘ K 

 Developer

 LM Studio Developer Docs API Changelog Core
 Server 

 Authentication Setup llmster as a Startup Task on Linux Run LM Studio as a service (headless) Using LM Link Using MCP via API Idle TTL and Auto-Evict REST API
 Overview Quickstart Stateful Chats Streaming events Chat with a model POST List your models GET Load a model POST Download a model POST Unload a model POST Get download status GET REST API v0 OpenAI Compatibility
 OpenAI Compatibility Endpoints Chat Completions Completions (Legacy) Embeddings List Models Responses Structured Output Tool Use Anthropic Compatibility
 Anthropic Compatibility Endpoints Messages 

 OpenAI Compatibility Endpoints 

 OpenAI Compatibility Endpoints
 Send requests to Responses, Chat Completions (text and images), Completions, and Embeddings endpoints.
 Copy Markdown Open Ask Bionic to read this page
 Copy this prompt, open Bionic, and paste it into a new chat.
 Read https://lmstudio.ai/docs/developer/openai-compat, I want to ask questions about it.

 Copy prompt 

 Supported endpoints 

 Endpoint Method Docs 
 /v1/models GET Models 
 /v1/responses POST Responses 
 /v1/chat/completions POST Chat Completions 
 /v1/embeddings POST Embeddings 
 /v1/completions POST Completions 

 Set the base url to point to LM Studio 

 You can reuse existing OpenAI clients (in Python, JS, C#, etc) by switching up the "base URL" property to point to your LM Studio instead of OpenAI's servers.

 Note: The following examples assume the server port is 1234 

 Python Example 

 from openai import OpenAI 

 client = OpenAI( 
 + base_url="http://localhost:1234/v1" 
 ) 

 # ... the rest of your code ... 

 Typescript Example 

 import OpenAI from 'openai'; 

 const client = new OpenAI({ 
 + baseUrl: "http://localhost:1234/v1" 
 }); 

 // ... the rest of your code ... 

 cURL Example 

 - curl https://api.openai.com/v1/chat/completions \ 
 + curl http://localhost:1234/v1/chat/completions \ 
 -H "Content-Type: application/json" \ 
 -d '{ 
 - "model": "gpt-4o-mini", 
 + "model": "use the model identifier from LM Studio here", 
 "messages": [{"role": "user", "content": "Say this is a test!"}], 
 "temperature": 0.7 
 }' 

 Using Codex with LM Studio 

 Codex is supported because LM Studio implements the OpenAI-compatible POST /v1/responses endpoint.

 See: Use Codex with LM Studio and Responses .

 Other OpenAI client libraries should have similar options to set the base URL.

 If you're running into trouble, hop onto our Discord and enter the #🔨-developers channel.

 REST API v0

 The REST API includes enhanced stats such as Token / Second and Time To First Token (TTFT), as well as rich information about models such as loaded vs unloaded, max context, quantization, and more.
 Chat Completions

 Send a chat history and get the assistant's response.

 On this page
 Supported endpoints Set the base url to point to LM Studio Python Example Typescript Example cURL Example Using Codex with LM Studio
