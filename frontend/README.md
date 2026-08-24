
# SmartSupport AI

## AI-Assisted Knowledge Base & Smart Support System

A modern support ticketing platform augmented with AI to reduce redundancy, accelerate resolution, and provide actionable insights for support teams.


## Table of Contents

- Overview
- Features
- Tech Stack
- Architecture
- Setup & Installation
- Usage
- AI & NLP Modules
- Analytics & Dashboards
- Contributing
## Overview

Support teams often face repetitive tickets, manual searches in knowledge bases, and slow onboarding for new agents.

SmartSupport AI leverages AI to:

- Auto-summarize tickets for faster understanding
- Cluster similar tickets to avoid duplicate work
- Suggest relevant knowledge base articles
- Provide actionable analytics and insights
- Guide new agents through a step-by-step onboarding workflow
## Features

### Ticket Management

- Create, update, and resolve support tickets
- Live AI-assisted ticket summaries
- Auto-generated post-resolution summaries

### Knowledge Base

- Semantic search using embeddings
- Article suggestions based on ticket content
- Full-text search for quick reference

### AI-Powered Enhancements

- Ticket similarity detection & clustering
- Suggested solutions from past tickets & KB
- Classification of tickets into categories

### Analytics & Insights

- Agent performance metrics
- Trending issues and topics
- Most used knowledge base articles

### Onboarding Workflow

- Guided KB reading
- Mock ticket handling
- Step-through AI hints for new agents


## Tech Stack

**Client:** React + TypeScript, Rich Text Editor, Dashboards

**Server:** Python (FastAPI), REST APIs, AI/NLP modules

**Database:** PostgreSQL, Vector DB, Redis Cache

**AI / NLP:** LLM APIs, Embedding search, Clustering & Classification


## Architecture

Frontend (React) ↔ Backend API (FastAPI) ↔ PostgreSQL + Elasticsearch + Vector DB
                                   ↔
                               AI/NLP Modules
                                   ↔
                             Redis Cache Layer

- Semantic Search: Vector embeddings + similarity scoring
- Clustering: Group similar tickets using k-means / DBSCAN
- Summarization: LLM-generated concise summaries
- Analytics: Dashboard powered by aggregated metrics

## Installation

Clone the repo

```bash
  git clone https://github.com/sreyangshu05/SmartSupport-AI.git
  cd SmartSupport-AI
  npm install
  npm run dev
```
    
## Environment Variables

To run this project, you will need to add the following environment variables to your .env file

`API_KEY`

`DATABASE_URL`

`REDIS_URL` 


## Usage

- Access the web app at http://localhost:3000
- Create tickets and observe AI-generated summaries
- Search knowledge base using natural language queries
- View analytics dashboards for insights
## AI & NLP Modules

- Summarization: Live & post-resolution summaries
- Clustering: Group tickets by semantic similarity
- Semantic Search: Vector embeddings for KB and ticket retrieval
- Classification: Categorize tickets for routing & reporting
## Analytics & Dashboards

- Agent metrics: average response time, ticket resolution time
- Trending issues/topics: visualize recurring problems
- KB usage: most-read articles & suggested solutions
## Contributing

- Fork the repository
- Create a feature branch: git checkout -b feature/your-feature
- Commit changes: git commit -m 'Add your feature'
- Push to branch: git push origin feature/your-feature
- Open a Pull Request

Contributions are always welcome!

Please adhere to this project's `code of conduct`.

