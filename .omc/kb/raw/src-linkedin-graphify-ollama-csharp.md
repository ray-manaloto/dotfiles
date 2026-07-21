How I Used Graphify + Ollama to Automatically Create Documentation for My C# Project (Fully Local Setup) 

 Agree & Join LinkedIn

 By clicking Continue to join or sign in, you agree to LinkedIn’s User Agreement , Privacy Policy , and Cookie Policy .

 Sign in to view more content

 Create your free account or sign in to continue your search 

 Email or phone

 Password

 Show 

 Forgot password? 

 Sign in

 Sign in with Email 

 or

 New to LinkedIn? Join now 

 By clicking Continue to join or sign in, you agree to LinkedIn’s User Agreement , Privacy Policy , and Cookie Policy .

 Skip to main content

 LinkedIn 

 Top Content

 People

 Learning

 Jobs

 Games

 Join now

 Sign in

 How I Used Graphify + Ollama to Automatically Create Documentation for My C# Project (Fully Local Setup)

 Report this article

 Sukanta Kumar Rout

 Sukanta Kumar Rout

 Published May 16, 2026

 + Follow

 As software projects grow, one thing almost always gets neglected: documentation. 

 Not because developers do not care about it, but because maintaining documentation manually is honestly exhausting. Architecture changes, services evolve, dependencies grow, and before long the documentation becomes outdated. 

 I recently started experimenting with a different approach using Graphify for knowledge graph generation, Ollama running local SLMs, and my existing C#/.NET microservice project. 

 The best part? Everything ran completely on my local machine. 

 No cloud APIs. 

 No sending source code externally. 

 No token costs. 

 Just local AI + knowledge graphs. 

 The Problem I Wanted to Solve 

 I have a fairly large C# project with: 

 - Multiple services 

 - Repository layers 

 - Database SDKs 

 - MQTT integrations 

 - Workflow orchestration 

 - Rule engine components 

 - Background workers 

 - REST APIs 

 After some time, understanding relationships inside the system became difficult. 

 Questions like these started becoming common: 

 - Which service calls this repository? 

 - Which APIs interact with telemetry data? 

 - What dependencies exist between modules? 

 - Which database tables are used by this service? 

 - How do workflows connect together? 

 I realized I needed something more intelligent than static documentation. 

 Why I Chose Graphify: 

 https://graphify.net/ 

 What I liked about Graphify is that it does not just “read files.” 

 It creates a connected knowledge graph of the project. 

 Instead of treating code as isolated files, it understands: 

 - classes 

 - functions 

 - imports 

 - dependencies 

 - relationships 

 - architecture flow 

 It also supports multimodal analysis, including: 

 - markdown 

 - PDFs 

 - diagrams 

 - screenshots 

 - architecture docs 

 My Local Setup: 

 I wanted everything fully local. 

 So I used: 

 - Graphify for repository analysis 

 - Ollama for local LLM inference 

 - Qwen2.5 model for reasoning 

 - ASP.NET Core for orchestration 

 Installing Ollama: 

 https://ollama.com/ 

ollama pull qwen2.5:7b
ollama serve

 That gave me a local AI endpoint running entirely on my PC. 

 No OpenAI API required. 

 Running Graphify 

 graphify - repo C:/Projects/MyCSharpPlatform 

 Graphify generated: 

 - graph.json 

 - graph.html 

 - architecture relationships 

 - dependency mappings 

 The graph visualization itself was already incredibly useful. 

 Recommended by LinkedIn

 Exploring Midjourney AI for Generating Software…

 Zaidul Alam

 3 years ago

 Implementing CQRS in a Go with Hexagonal Architecture

 David Alecrim

 1 year ago

 AI Meets Software Architecture: A Paradigm Shift

 Luqman Shareef Mohammed

 1 year ago

 Using AI to Generate Documentation: 

 Instead of manually writing documentation, I started feeding selected graph context into the local SLM. 

 The key lesson I learned: 

 DO NOT send the entire graph to the model. 

 Initially I tried that and quickly ran into: 

 - huge prompts 

 - timeout issues 

 - slow inference 

 - memory problems 

 The better approach was: 

 1. Retrieve only relevant graph nodes 

 2. Build focused prompts 

 3. Ask the model to summarize architecture 

 That changed everything. 

 Example Prompt: 

 Explain the architecture of the telemetry ingestion pipeline. 

 Focus on: 

 - API layer 

 - Repository layer 

 - MQTT flow 

 - Database interactions 

 - Workflow processing 

 The model started generating surprisingly useful documentation. 

 Not generic AI fluff. Actual architecture-aware explanations. 

 One thing I did not initially expect was how useful this became for onboarding. 

 A new developer normally spends days trying to understand: 

 - folder structure 

 - service interactions 

 - hidden dependencies 

 - business logic flow 

 But with this setup, I could ask: 

 - Which services interact with telemetry processing? 

 - Explain how MQTT data flows through the platform. 

 And the system produced understandable summaries immediately. 

 “Why Running Everything Locally Matters” 

 This was probably the most important part for me. 

 Many AI tooling workflows today require: 

 - cloud APIs 

 - uploading repositories 

 - external processing 

 - expensive token usage 

 I did not want my source code leaving my machine. 

 Using: 

 - Graphify 

 - Ollama 

 - local SLMs 

 Gave me: 

 - privacy 

 - offline capability 

 - no API cost 

 - full control 

 - low latency 

 Models I Tested during this POC work 

 I experimented with several local models. 

 For my use case, Qwen2.5:7b gave the best overall results. 

 Final Thoughts… 

 I originally started this project simply trying to automate documentation for my C# project. 

 But after combining: 

 Graphify knowledge graphs 

 Ollama local SLMs 

 AI-assisted retrieval 

 It started feeling like I had built a local engineering intelligence system. 

 The most exciting part is that all of this runs completely offline on a normal PC. 

 No cloud dependency. 

 No expensive APIs. 

 No external code sharing. 

 Just your project, your machine, and local AI helping you understand your own architecture better. 

 And honestly, I think this kind of workflow is going to become much more common for software teams in the future. 

 Like 

 Like 

 Celebrate 

 Support 

 Love 

 Insightful 

 Funny 

 Comment

 Copy 

 LinkedIn 

 Facebook 

 X 

 Share

 8

 1 Comment

 Gobinda Goswami Jena

 1mo

 Report this comment

 This is super useful Sukanta , thanks for sharing.

 Like

 Reply

 1 Reaction

 2 Reactions

 To view or add a comment, sign in 

 More articles by Sukanta Kumar Rout

 MTConnect Enabling Data-Driven Manufacturing

 Jul 19, 2024 

 MTConnect Enabling Data-Driven Manufacturing

 Background: So, why I am discussing this today, let me tell you. Sometimes back I was working for a customer project…

 6

 Standards used for Smart Manufacturing : An Overview

 Apr 6, 2024 

 Standards used for Smart Manufacturing : An Overview

 Overview: What is Smart Manufacturing? Please go through the link to get an overview of smart manufacturing before we…

 8

 Is a "Data Mesh" Architecture fits to modern Smart Factory?

 Dec 28, 2023 

 Is a "Data Mesh" Architecture fits to modern Smart Factory?

 Overview: In today’s digital economy, every business wants to be data driven. It is one of the top strategic goals of…

 11

 A reference Architecture for Intelligence at Edge

 Oct 9, 2023 

 A reference Architecture for Intelligence at Edge

 Background: In one of my previous articles Edge SW Stack we discussed about the components and architecture of it. A…

 4

 2 Comments

 IoT hub or Event hub, which one to use and how should we use it?

 Aug 18, 2023 

 IoT hub or Event hub, which one to use and how should we use it?

 Background:- IoT applications and other on-prem applications are generating millions of data points daily. It is…

 15

 1 Comment

 "OEE" looking in a different angle

 Jul 28, 2023 

 "OEE" looking in a different angle

 Background..

 14

 1 Comment

 An IIOT Architecture with MQTT and Sparkplug B

 Jul 18, 2023 

 An IIOT Architecture with MQTT and Sparkplug B

 Let's Start with..

 15

 1 Comment

 Enterprise Architecture:- What ,Why and How?

 Jun 26, 2023 

 Enterprise Architecture:- What ,Why and How?

 Rd I started as a software developer to become a solution architect. During my journey my thought process was different…

 12

 1 Comment

 An overview of IIOT Edge Software Stack

 Jun 2, 2023 

 An overview of IIOT Edge Software Stack

 In the era of IOT and IIOT(Industrial Internet of Things) there is a growing demand to deploy solutions at the edge and…

 14

 Implementing a rule engine

 May 24, 2023 

 Implementing a rule engine

 Some months back i was working for an edge software framework using the dot net core c#. As part of the edge platform…

 7

 1 Comment

 Show more

 See all articles

 Others also viewed

 Good Practices on RESTful API Modeling (Part 1)

 Thomas Lee

 7y

 Model Context Protocol (MCP) – Internal Detailed Architecture

 Rajesh Paleru

 10mo

 AI Tool That Turns Diagrams Into Production APIs in Seconds

 Ayush Dixit

 5mo

 Model Context Protocol (MCP): The REST/JSON of Agentic AI Architecture?

 Shyam Ramamurthy

 9mo

 Model Context Protocol - AIShorts #1

 Keep Up

 1y

 Article 2 of 10, Part 1 of 4 | HyperRE TechFlow Edition #16

 Tavi T.

 1y

 🔄 Evolving from RASA to LangGraph: Embracing the MCP Paradigm

 Vishal Parekh

 1y

 Reimagining API Handlers with Pipeline Workflow: A Maintainable Approach to Vertical Slices.

 Kishor Naik

 1y

 Platform Pulse #9: Hardening the Control Plane and the Rise of Architectural Middleware

 Goran Minov

 2mo

 The Paradigm Shift in Software Architecture with GenAI, LLM, RAG, and Agentic Technologies

 Sachidanand Sharma

 1y

 Show more

 Show less

 Similar topics

 How to Use Knowledge Graphs in Llms

 10 Posts

 6,700

 Benefits of Using Knowledge Graphs

 10 Posts

 5,951

 How to Automate Document Workflows

 10 Posts

 1,071

 Using Local LLMs to Improve Generative AI Models

 4 Posts

 578

 Lightweight LLM Solutions for Knowledge Graph QA

 5 Posts

 1,854

 How Knowledge Graphs Improve AI

 10 Posts

 5,292

 Using LLMs as Microservices in Application Development

 5 Posts

 480

 Open Source AI Developments Using Llama

 10 Posts

 3,358

 How to Understand REST and Graphql APIs

 5 Posts

 1,517

 Show more

 Show less

 Explore content categories

 Career 

 Productivity 

 Finance 

 Soft Skills & Emotional Intelligence 

 Project Management 

 Education 

 Technology 

 Leadership 

 Ecommerce 

 User Experience 

 Recruitment & HR 

 Customer Experience 

 Real Estate 

 Marketing 

 Sales 

 Retail & Merchandising 

 Science 

 Supply Chain Management 

 Future Of Work 

 Consulting 

 Writing 

 Economics 

 Artificial Intelligence 

 Employee Experience 

 Workplace Trends 

 Fundraising 

 Networking 

 Corporate Social Responsibility 

 Negotiation 

 Communication 

 Engineering 

 Hospitality & Tourism 

 Business Strategy 

 Change Management 

 Organizational Culture 

 Design 

 Innovation 

 Event Planning 

 Training & Development 

 Show more

 Show less

 LinkedIn 

 © 2026 

 About

 Accessibility

 User Agreement

 Privacy Policy

 Your California Privacy Choices

 Cookie Policy

 Copyright Policy

 Brand Policy

 Guest Controls

 Community Guidelines

 العربية (Arabic)

 বাংলা (Bangla)

 Čeština (Czech)

 Dansk (Danish)

 Deutsch (German)

 Ελληνικά (Greek)

 English (English) 

 Español (Spanish)

 فارسی (Persian)

 Suomi (Finnish)

 Français (French)

 हिंदी (Hindi)

 Magyar (Hungarian)

 Bahasa Indonesia (Indonesian)

 Italiano (Italian)

 עברית (Hebrew)

 日本語 (Japanese)

 한국어 (Korean)

 मराठी (Marathi)

 Bahasa Malaysia (Malay)

 Nederlands (Dutch)

 Norsk (Norwegian)

 ਪੰਜਾਬੀ (Punjabi)

 Polski (Polish)

 Português (Portuguese)

 Română (Romanian)

 Русский (Russian)

 Svenska (Swedish)

 తెలుగు (Telugu)

 ภาษาไทย (Thai)

 Tagalog (Tagalog)

 Türkçe (Turkish)

 Українська (Ukrainian)

 Tiếng Việt (Vietnamese)

 简体中文 (Chinese (Simplified))

 正體中文 (Chinese (Traditional))

 Language
