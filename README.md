# SupportPilot — LLM-Powered Customer Support Platform

> **Practice & Learning Project**
>
> SupportPilot is a practice project built to explore how Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), APIs, and modern web technologies can be combined to build an AI-assisted customer support system.
>
> The information currently included in the knowledge base is for **practice, testing, and demonstration purposes only**. It does not represent the official policies, services, or business information of any real company or agency.
>
> **Designed to be customizable:** SupportPilot can be adapted for different companies, agencies, businesses, or organizations by replacing the demonstration knowledge-base content with their own verified information, FAQs, product documentation, policies, service details, and operational guidelines. With the appropriate configuration and development, the same underlying approach can support different organizational requirements without having to build an entirely new system from scratch.
>
> This repository demonstrates a technical foundation for an AI support application. It is not a production-ready enterprise deployment, and additional security, testing, integration, and operational work would be required before real-world use.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Practice Scope and Customization](#practice-scope-and-customization)
- [Key Features](#key-features)
- [How It Works](#how-it-works)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Environment Configuration](#environment-configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Evaluation](#evaluation)
- [Security and Production Considerations](#security-and-production-considerations)
- [Future Improvements](#future-improvements)
- [Author](#author)

---

## Project Overview

SupportPilot is a full-stack, LLM-powered customer support application developed as a practical learning project.

The goal is to explore how AI can assist support teams with customer requests, ticket classification, knowledge-based answers, and support workflows through a structured backend API and an interactive web interface.

The project brings together:

- A FastAPI backend for API endpoints and application logic.
- LLM integration for AI-assisted processing of support requests.
- A knowledge base containing support-related information.
- Retrieval-based context to help ground AI responses in relevant information.
- Database models and persistence for application data.
- Authentication-related backend functionality.
- A React and TypeScript frontend.
- An evaluation workflow for testing model behavior.

The project provides a foundation for understanding how an AI customer support system can be designed, implemented, tested, and extended.

## Practice Scope and Customization

### Current Version: Demonstration Data

The current knowledge base contains sample support information intended for experimentation and testing. AI responses may reflect this sample content and should not be treated as authoritative information about a real business.

The demonstration content should be replaced or reviewed before the application is used for an actual organization.

### Adapting SupportPilot to a Real Organization

SupportPilot follows a reusable approach: the knowledge and configuration used by the AI can be tailored to the organization that will use the system.

For example, the platform could be adapted for:

| Organization | Example knowledge-base content |
|---|---|
| E-commerce company | Product details, shipping policies, refunds, returns, and order FAQs |
| Software company | Product documentation, troubleshooting guides, account support, and technical FAQs |
| Digital marketing agency | Service packages, onboarding instructions, campaign processes, and client FAQs |
| Educational institution | Admissions information, course details, fee policies, and student support |
| Healthcare organization | Approved administrative FAQs, appointment procedures, and service information, subject to applicable privacy and compliance requirements |
| Financial services company | Approved product documentation, account procedures, and customer service policies, subject to regulatory requirements |

These are potential use cases, not claims that integrations or industry-specific compliance features have already been implemented.

### What Would Change for Each Organization?

To adapt the project, an implementation team would typically:

1. **Collect verified information:** Gather the organization's approved FAQs, policies, documentation, service details, and support procedures.
2. **Prepare the knowledge base:** Organize the information into suitable documents and formats.
3. **Configure retrieval:** Ensure relevant information can be retrieved for incoming customer questions.
4. **Customize prompts:** Define the AI's role, response style, boundaries, escalation rules, and instructions.
5. **Configure workflows:** Adapt ticket categories, urgency levels, support teams, and business rules.
6. **Integrate business systems:** Connect approved APIs or services if the organization needs CRM, order management, help-desk, or other integrations.
7. **Evaluate responses:** Test the system against organization-specific questions and expected answers.
8. **Apply production safeguards:** Implement appropriate access controls, privacy protections, monitoring, error handling, and human escalation.

The precise changes depend on the organization's requirements and the capabilities implemented in its deployment.

**Important:** Adding documents to a knowledge base alone does not automatically make the system production-ready. Retrieval configuration, prompt design, evaluation, integrations, and security controls must also be reviewed.

---

## Key Features

### 1. LLM-Based Ticket Triage

The backend includes an LLM-powered triage workflow designed to analyze customer support requests and produce structured information such as:

- **Category:** The type of issue reported.
- **Urgency:** The assigned priority level.
- **Suggested team:** The team that may be responsible for handling the request.
- **Confidence:** The model's reported confidence score.
- **Reason:** An explanation of the classification.

The output structure is designed to make model responses easier for an application to process.

LLM-generated classifications should be validated and reviewed according to the needs of the organization using the system.

### 2. AI-Assisted Support Responses

The project includes AI-assisted functionality for generating responses to support-related questions.

Relevant knowledge-base information can provide additional context for response generation, helping the application use supplied documentation rather than relying exclusively on the model's general knowledge.

The accuracy of answers depends on the quality, relevance, completeness, and freshness of the available information.

### 3. Knowledge Base and Retrieval

The `knowledge_base/` directory stores support-related documentation used by the project.

This provides a starting point for experimenting with Retrieval-Augmented Generation (RAG), in which relevant source information is retrieved and supplied as context to an LLM.

The knowledge base is intended to be replaceable so the project can be adapted to different information domains.

### 4. Support Ticket API

The backend contains support-related routes for application workflows such as ticket creation, ticket retrieval, and conversation handling.

The exact operations and permissions available are defined by the implemented API routes.

### 5. Database Layer

The application includes database configuration and model modules for managing application data.

SQLite is used for local development in the current setup. A production deployment may require a different database architecture based on concurrency, reliability, backup, and operational requirements.

### 6. Authentication-Related Functionality

The backend includes authentication-related code and database models.

The authentication and authorization behavior should be reviewed against the actual route configuration before the application is exposed to external users.

### 7. React Frontend

The frontend uses React and TypeScript, with Vite for local development.

It provides the web interface through which users can interact with the support application and its backend services.

### 8. Evaluation Workflow

The `Evaluations/` directory contains evaluation cases, saved results, and a Python evaluation script.

These resources provide a starting point for testing AI behavior and assessing whether outputs meet defined expectations.

---

## How It Works

The following describes the intended high-level workflow:

1. A user submits a support request through the web interface or an available API endpoint.
2. The backend validates the incoming request.
3. Ticket information is processed and stored where supported by the implemented workflow.
4. The triage component sends the appropriate input to the configured LLM.
5. The LLM returns structured classification information.
6. For AI-assisted answers, relevant knowledge-base content can be retrieved and used as context.
7. The generated result is returned through the backend to the frontend.
8. Evaluation cases can be used to test selected AI behaviors.

The exact request flow depends on the implementation of the relevant API routes and service functions.

## System Architecture

```text
                 User / Support Agent
                          |
                          v
               React + TypeScript UI
                       (Vite)
                          |
                     HTTP Requests
                          |
                          v
                   FastAPI Backend
                          |
             +------------+------------+
             |            |            |
             v            v            v
        Ticket API    LLM Triage   Authentication
             |            |            |
             |            v            |
             |       LLM Provider       |
             |                         |
             +------------+------------+
                          |
                          v
                    Database Layer
                          |
                          v
                  Local SQLite Database


      Knowledge Base ---> Retrieval ---> LLM Context
                                             |
                                             v
                                      AI-Assisted Answer


      Evaluation Cases ---> Evaluation Script ---> Results
```

This is a conceptual architecture diagram. It illustrates the main components and intended relationships rather than guaranteeing that every request passes through every component.

---

## Technology Stack

| Area | Technology |
|---|---|
| Backend language | Python |
| Backend framework | FastAPI |
| API server | Uvicorn |
| Request/response validation | Pydantic |
| Frontend framework | React |
| Frontend language | TypeScript |
| Frontend development server | Vite |
| Package management | npm |
| Database | SQLite for local development |
| AI capability | External LLM API |
| Knowledge grounding | Knowledge-base retrieval / RAG workflow |
| Configuration | Environment variables |
| Evaluation | Python scripts and JSON test data |
| Version control | Git and GitHub |

---

## Project Structure

```text
LLM production API/
|
|-- app/
|   |-- main.py
|   |-- llm.py
|   |-- support_router.py
|   |-- auth.py
|   |-- database.py
|   |-- database_models.py
|   |-- models.py
|   |-- schemas.py
|   |-- seed.py
|   |-- hello.py
|
|-- frontend/
|   |-- src/
|   |   |-- App.tsx
|   |   |-- App.css
|   |   |-- index.css
|   |   |-- main.tsx
|   |-- public/
|   |-- package.json
|   |-- vite.config.ts
|
|-- knowledge_base/
|   |-- support_faq.md
|
|-- prompts/
|   |-- triage-v1.md
|
|-- Evaluations/
|   |-- cases.json
|   |-- results.json
|   |-- run_evaluation.py
|
|-- images/
|-- videos/
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- JOB-CARD.md
|-- README.md
```

---

## Prerequisites

Before running the project, install:

- Python 3.13, recommended for the current development setup.
- Node.js and npm.
- Git.
- A valid API key for the LLM provider configured in the backend.

Verify the installations:

```powershell
python --version
node --version
npm --version
git --version
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/HadiaWaheed/LLM-behind-API.git
cd LLM-behind-API
```

### 2. Create a Python Virtual Environment

On Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If you already have a virtual environment, activate it rather than creating another one.

### 3. Install Backend Dependencies

From the repository root:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root using `.env.example` as a reference.

Add the actual values required by the backend configuration and LLM integration. Check the configuration code for the exact variable names.

Do not commit `.env` or put API keys in source code.

### 5. Install Frontend Dependencies

Open a second terminal and move to the frontend directory:

```powershell
cd frontend
npm install
```

---

## Running the Application

The backend and frontend run in separate terminals.

### Terminal 1: Start the Backend

From the repository root, activate the virtual environment and run:

```powershell
python -m uvicorn app.main:app --reload
```

The backend should be available at:

- **API base URL:** http://127.0.0.1:8000
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

Keep this terminal open while using the application.

### Terminal 2: Start the Frontend

Open another terminal:

```powershell
cd frontend
npm run dev
```

Vite will display the local development URL. In the current setup, it is:

http://localhost:5173/

Open the URL in your browser.

**Both services must be running** for the frontend to communicate with the local backend.

If the frontend cannot connect to the API, check that the backend is running and review the frontend's API base URL configuration.

---

## API Documentation

FastAPI's interactive documentation is available when the backend is running:

**http://127.0.0.1:8000/docs**

Use Swagger UI to:

- Inspect the available routes.
- Review request and response schemas.
- Submit test requests.
- Examine HTTP status codes and responses.
- Check which routes require authentication.

The live API documentation is the source of truth for actual route paths, HTTP methods, parameters, and permissions.

---

## Evaluation

The `Evaluations/` directory includes:

- `cases.json` — evaluation inputs.
- `results.json` — saved evaluation output.
- `run_evaluation.py` — evaluation runner.

Review `run_evaluation.py` to confirm the required arguments, environment configuration, and execution command before running it.

Evaluation results depend on the test data, model configuration, and criteria used. They should not be interpreted as a guarantee of production performance.

---

## Security and Production Considerations

This repository is a practice project. Additional work is required before using it with real customers or business data.

For a production deployment, review and implement appropriate measures for:

- Authentication and authorization.
- API key and secret management.
- Privacy and handling of personal or confidential information.
- Input validation and output validation.
- Human review and escalation of uncertain AI decisions.
- Logging, monitoring, and error handling.
- Rate limiting and abuse prevention.
- Database backups and migrations.
- Testing and evaluation against realistic, organization-specific cases.
- Applicable legal, regulatory, and industry requirements.

Only use information that the organization is authorized to process. Do not upload confidential company documents or customer data without appropriate approval and safeguards.

---

## Future Improvements

Potential areas for further development include:

- More comprehensive automated tests.
- Expanded evaluation datasets and regression testing.
- Improved observability and request tracing.
- Organization-specific configuration and knowledge-base management.
- More advanced role-based access control.
- Integrations with approved CRM and help-desk platforms.
- Production database and deployment configuration.
- Human escalation workflows and monitoring of AI quality.

These are potential improvements and should not be interpreted as features already implemented.

---

## Author

**Hadia Waheed**

- **Email:** [hadiawaheed5@gmail.com](mailto:hadiawaheed5@gmail.com)
- **LinkedIn:** *https://www.linkedin.com/in/hadia-waheed-1647892aa/*

---

## Project Status

This project is intended for learning, experimentation, and demonstration of LLM-powered application development. Its architecture and knowledge-base approach can serve as a starting point for organization-specific solutions after the necessary customization, testing, and production hardening.

