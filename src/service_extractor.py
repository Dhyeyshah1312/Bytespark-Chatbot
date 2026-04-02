import re

def extract_services_from_docs(docs):

    full_text = "\n".join([doc.page_content for doc in docs])

    pattern = r"\d+\)\s.*?(?=\n\d+\)|$)"
    matches = re.findall(pattern, full_text, re.DOTALL)

    services = []
    service_names = []

    for match in matches:
        services.append(match.strip())

        name_match = re.match(r"\d+\)\s*(.*?):", match)
        if name_match:
            service_names.append(name_match.group(1).strip())

    return services, service_names