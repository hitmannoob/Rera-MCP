from mcp.server.fastmcp import FastMCP
import base64
import io
from PyPDF2 import PdfReader
from pydantic.types import SecretStr
import requests
import pandas as pd
from bs4 import BeautifulSoup
from openai import OpenAI
from fastapi import FastAPI, Request # type: ignore
from fastapi.responses import HTMLResponse, StreamingResponse ,JSONResponse  # type: ignore
from fastapi.templating import Jinja2Templates # type: ignore
from pydantic import BaseModel
import openai  # Optional: remove if not using OpenAI
import os
import difflib
import requests
from typing import List, Literal
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
print("Code is running")

mcp = FastMCP("GPT_RERA")
class variable():
    def __init__(self) -> None:
        self.project_list = [] 


variable_class = variable()
@mcp.tool()
def get_list_of_projects(project_name: str) :
    """Get the list of projects from the Maharashtra RERA website. when user gives a project name , it will return the list of projects with that name."""  
    payload ={
            "project_name": project_name
    }
    base_url = "https://maharera.maharashtra.gov.in/projects-search-result"
    response = requests.get(base_url, params= payload)
    # return response.status_code
    if response.status_code== 200:
        soup =   BeautifulSoup(response.content, 'html.parser')
        project_list = soup.find('div' , class_ ="alert alert-danger center")
        if project_list is not None:
            return "No Project Found please enter the correct project name"
        
        divs = soup.find_all('div', class_='row shadow p-3 mb-5 bg-body rounded')
        data_list = []
        for div in divs:
            soup = BeautifulSoup(str(div), 'html.parser')
            h4_tag = soup.find('h4')
            project_name = h4_tag.text if h4_tag is not None else "N/A"
            builder_tag = soup.find('p', class_="darkBlue bold")
            builder_name = builder_tag.text if builder_tag is not None else "N/A"
            district_pincode = soup.find_all("p")[2:]
            project_id = soup.find('a', class_ = "hsmdata click-modal viewLink")
            district= district_pincode[2].text
            pincode = district_pincode[1].text
            doc_id = project_id['data-hqstr'] # type: ignore
            data = {
                "Project_Name": project_name,
                "Builder_Name": builder_name,
                "District": district,
                "Pincode": pincode,
                "Doc_id": doc_id

            }
            data_list.append(data)
    
    else:
        return "Something went wrong while fetching the projects. Please try again later."


    variable_class.project_list = data_list

    return data_list



@mcp.tool()
def get_exact_project_details(project_name: str) :
    """"when user provides a exact name of the project this tool will return the details of the project"""
    data_list = variable_class.project_list
    if not isinstance(data_list, list):
        # If data_list is not a list, it's an error message string
        return data_list
    project_df = pd.DataFrame(data_list)
    project_name_list = list(project_df['Project_Name'])
    closest_project_name = difflib.get_close_matches(project_name, project_name_list)
    pdf_doc_id = project_df[project_df['Project_Name']== closest_project_name[0]]['Doc_id'].values[0]

    pdf_text = get_pdf_content(str(pdf_doc_id))
    return pdf_text


def get_pdf_content(doc_id: str):
    base_certi = f"https://maharera.maharashtra.gov.in/project-document?id={doc_id}&type=DocProjectHSMViewCert"
    response = requests.get(base_certi)
    soup = BeautifulSoup(response.text, 'html.parser')
    link = soup.find('object',)
    file_bytes = base64.b64decode(link['data'].split(",")[1], validate=True) # type: ignore
    pdf_memory = io.BytesIO(file_bytes)
    reader = PdfReader(pdf_memory)
    pdf_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    return pdf_text


if __name__ == "__main__":
    print("Starting the server")
    mcp.run(transport="stdio")
