
"""Script to safely unregister/delete agents from Gemini Enterprise."""

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

# Terminal coloring helpers
class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"

def log_info(msg):
    print(f"{Style.BLUE}ℹ{Style.RESET} {msg}")

def log_success(msg):
    print(f"{Style.GREEN}✔{Style.RESET} {msg}")

def log_warning(msg):
    print(f"{Style.YELLOW}⚠{Style.RESET} {msg}")

def log_error(msg):
    print(f"{Style.RED}✘{Style.RESET} {msg}", file=sys.stderr)

def log_banner(title):
    border = "=" * 60
    print(f"\n{Style.CYAN}{border}")
    print(f"{Style.BOLD}{title.center(60)}")
    print(f"{Style.CYAN}{border}{Style.RESET}\n")

def run_command(args):
    """Run a local shell command and return its stdout."""
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Command {' '.join(args)} failed: {e.stderr.strip()}")
    except FileNotFoundError:
        raise RuntimeError(f"Required command '{args[0]}' is not installed or not in PATH.")

def get_gcloud_token():
    """Get active gcloud access token."""
    log_info("Fetching gcloud access token...")
    return run_command(["gcloud", "auth", "print-access-token"])

def get_current_project():
    """Get default GCP project ID."""
    try:
        project_id = run_command(["gcloud", "config", "get-value", "project"])
        if project_id and project_id != "(unset)":
            return project_id
    except Exception:
        pass
    return None

def get_project_number(project_id):
    """Resolve project number from project ID."""
    log_info(f"Resolving project number for '{project_id}'...")
    try:
        return run_command([
            "gcloud", "projects", "describe", project_id, 
            "--format=value(projectNumber)"
        ])
    except Exception as e:
        log_warning(f"Could not resolve project number automatically: {e}")
        return None

def parse_gemini_enterprise_app_id(app_id):
    """Parse app resource name into components."""
    pattern = r"^projects/([^/]+)/locations/([^/]+)/collections/([^/]+)/engines/([^/]+)$"
    match = re.match(pattern, app_id.strip())
    if match:
        return {
            "project_number": match.group(1),
            "location": match.group(2),
            "collection": match.group(3),
            "engine_id": match.group(4)
        }
    return None

def get_discovery_engine_endpoint(location):
    """Get Discovery Engine API endpoint for the location."""
    if location == "global":
        return "https://discoveryengine.googleapis.com"
    return f"https://{location}-discoveryengine.googleapis.com"

def make_request(url, headers, method="GET", payload=None):
    """Send an HTTP request using Python's standard library."""
    data = None
    if payload:
        data = json.dumps(payload).encode("utf-8")
        headers = headers.copy()
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, headers=headers, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res_body = response.read().decode("utf-8")
            return json.loads(res_body) if res_body else {}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        try:
            err_json = json.loads(err_msg)
            message = err_json.get("error", {}).get("message", err_msg)
        except Exception:
            message = err_msg
        raise RuntimeError(f"HTTP Error {e.code}: {message}")
    except Exception as e:
        raise RuntimeError(f"Network error: {e}")

def fetch_gemini_enterprise_apps(project_number, headers):
    """Search for Gemini Enterprise apps across common locations."""
    log_info("Searching for Gemini Enterprise apps in your project...")
    all_apps = []
    locations = ["global", "us", "eu"]
    for loc in locations:
        base_endpoint = get_discovery_engine_endpoint(loc)
        url = f"{base_endpoint}/v1alpha/projects/{project_number}/locations/{loc}/collections/default_collection/engines"
        try:
            res = make_request(url, headers)
            engines = res.get("engines", [])
            for e in engines:
                if e.get("appType") == "APP_TYPE_INTRANET":
                    e["_location"] = loc
                    all_apps.append(e)
        except Exception:
            pass
    return all_apps

def get_current_user_email():
    """Get the active gcloud account email."""
    try:
        return run_command(["gcloud", "config", "get-value", "account"])
    except Exception:
        return None

def fetch_agents_by_creator(project_id, creator_email, freshness="30d"):
    """Query GCP Audit Logs to find all agents created by a specific user email."""
    log_info(f"Querying audit logs for agents created by {Style.BOLD}{creator_email}{Style.RESET} with a lookback of {Style.BOLD}{freshness}{Style.RESET}...")
    
    query = (
        f'resource.type="audited_resource" AND '
        f'protoPayload.methodName="google.cloud.discoveryengine.v1main.AgentService.CreateAgent" AND '
        f'protoPayload.authenticationInfo.principalEmail="{creator_email}"'
    )
    
    try:
        logs_json = run_command([
            "gcloud", "logging", "read", query,
            f"--project={project_id}",
            f"--freshness={freshness}",
            "--format=json",
            "--limit=50"
        ])
        
        if not logs_json or logs_json == "[]":
            return []
            
        entries = json.loads(logs_json)
        agent_names = set()
        for entry in entries:
            payload = entry.get("protoPayload", {})
            agent_name = payload.get("response", {}).get("name")
            if not agent_name:
                agent_name = payload.get("resourceName")
                
            if agent_name and "/agents/" in agent_name:
                agent_names.add(agent_name)
                
        return sorted(list(agent_names))
    except Exception as e:
        log_warning(f"Failed to query audit logs: {e}")
        return []

def fetch_agent_details(agent_name, access_token):
    """Fetch details of a single agent to verify it still exists."""
    parts = agent_name.split("/")
    if len(parts) < 4:
        return None
    project_number = parts[1]
    location = parts[3]
    
    base_endpoint = get_discovery_engine_endpoint(location)
    url = f"{base_endpoint}/v1alpha/{agent_name}"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-goog-user-project": project_number,
        "User-Agent": "google-agents-cli/delete-script"
    }
    try:
        return make_request(url, headers)
    except Exception:
        return None

def print_agent_list(agents_to_display):
    """Print a clean, styled list of agents."""
    for idx, item in enumerate(agents_to_display, 1):
        agent = item["api_object"]
        agent_name = item["name"]
        short_agent_id = agent_name.split("/")[-1]
        display_name = agent.get("displayName", "N/A")
        description = agent.get("description", "No description")
        app_id = item["app_id"]
        
        # Determine registration type
        agent_type = "ADK Agent"
        target_info = "N/A"
        if "adk_agent_definition" in agent:
            agent_type = "ADK Agent"
            target_info = agent.get("adk_agent_definition", {}).get(
                "provisioned_reasoning_engine", {}
            ).get("reasoning_engine", "N/A")
        elif "adkAgentDefinition" in agent:
            agent_type = "ADK Agent"
            target_info = agent.get("adkAgentDefinition", {}).get(
                "provisionedReasoningEngine", {}
            ).get("reasoningEngine", "N/A")
        elif "a2aAgentDefinition" in agent:
            agent_type = "A2A Agent"
            try:
                card_str = agent.get("a2aAgentDefinition", {}).get("jsonAgentCard", "{}")
                card = json.loads(card_str)
                target_info = card.get("url", "N/A")
            except Exception:
                target_info = "A2A Card JSON"
        elif "a2a_agent_definition" in agent:
            agent_type = "A2A Agent"
            try:
                card_str = agent.get("a2a_agent_definition", {}).get("json_agent_card", "{}")
                card = json.loads(card_str)
                target_info = card.get("url", "N/A")
            except Exception:
                target_info = "A2A Card JSON"

        print(f"  {Style.GREEN}[{idx}]{Style.RESET} {Style.BOLD}{display_name}{Style.RESET} ({Style.CYAN}{agent_type}{Style.RESET})")
        print(f"      App/Engine ID: {Style.BOLD}{app_id}{Style.RESET}")
        print(f"      Agent ID:      {short_agent_id}")
        print(f"      Target:        {Style.DIM}{target_info}{Style.RESET}")
        print(f"      Desc:          {Style.DIM}{description}{Style.RESET}\n")

def main():
    log_banner("GEMINI ENTERPRISE — AGENT UNREGISTER TOOL")

    try:
        # Check auth & project first
        access_token = get_gcloud_token()
    except Exception as e:
        log_error(f"Authentication failed: {e}")
        log_info("Please run: gcloud auth application-default login && gcloud auth login")
        sys.exit(1)

    # Resolve project ID & number
    project_id = get_current_project()
    project_number = None
    if project_id:
        log_success(f"Default project ID detected: {Style.BOLD}{project_id}{Style.RESET}")
        project_number = get_project_number(project_id)
        if project_number:
            log_success(f"Resolved project number: {Style.BOLD}{project_number}{Style.RESET}")
    else:
        log_warning("No default GCP project set in gcloud. Audit log search will require manually typing project ID.")

    print(f"\n{Style.BOLD}How do you want to locate the agent to delete?{Style.RESET}")
    print(f"  {Style.GREEN}[1]{Style.RESET} Browse/Select by Gemini Enterprise App (standard flow)")
    print(f"  {Style.GREEN}[2]{Style.RESET} Search by Creator Email (uses GCP Audit Logs)")
    
    find_choice = "1"
    while True:
        choice = input(f"\n{Style.CYAN}Select an option (1 or 2) [1]: {Style.RESET}").strip() or "1"
        if choice in ("1", "2"):
            find_choice = choice
            break

    agents_to_display = []

    if find_choice == "1":
        # Standard Flow: Browse by App
        discovered_apps = []
        headers_for_discovery = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "google-agents-cli/delete-script"
        }
        if project_number:
            headers_for_discovery["x-goog-user-project"] = project_number
            try:
                discovered_apps = fetch_gemini_enterprise_apps(project_number, headers_for_discovery)
            except Exception as e:
                log_warning(f"Could not auto-discover apps: {e}")

        selected_app = None
        if discovered_apps:
            print(f"\n{Style.BOLD}Step 1: Select Gemini Enterprise App{Style.RESET}")
            log_success(f"Discovered {len(discovered_apps)} Gemini Enterprise app(s):")
            for idx, app in enumerate(discovered_apps, 1):
                disp_name = app.get("displayName", "N/A")
                eng_id = app.get("name", "").split("/")[-1]
                loc = app.get("_location", "global")
                print(f"  {Style.GREEN}[{idx}]{Style.RESET} {Style.BOLD}{disp_name}{Style.RESET} (location: {loc})")
                print(f"      Engine ID: {Style.DIM}{eng_id}{Style.RESET}")
            
            print(f"  {Style.GREEN}[0]{Style.RESET} Enter a custom App/Engine ID manually")
            
            while True:
                try:
                    sel = input(f"\n{Style.CYAN}Select an app (0-{len(discovered_apps)}): {Style.RESET}").strip()
                    if not sel:
                        continue
                    sel_idx = int(sel)
                    if 0 <= sel_idx <= len(discovered_apps):
                        if sel_idx > 0:
                            selected_app = discovered_apps[sel_idx - 1]
                        break
                    else:
                        print(f"Please enter a number between 0 and {len(discovered_apps)}")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")

        if selected_app:
            full_app_id = selected_app.get("name")
            parsed = parse_gemini_enterprise_app_id(full_app_id)
            if parsed:
                project_number = parsed["project_number"]
                location = parsed["location"]
                collection = parsed["collection"]
                engine_id = parsed["engine_id"]
            else:
                log_error("Could not parse selected app metadata.")
                sys.exit(1)
        else:
            # Fallback manual input flow
            print(f"\n{Style.BOLD}Step 1: Enter Gemini Enterprise App ID{Style.RESET}")
            print("Format: projects/{project_number}/locations/{location}/collections/default_collection/engines/{engine_id}")
            print("Or enter the short App/Engine ID directly if using default project & 'global' location.")
            
            app_id_input = input(f"{Style.CYAN}Gemini Enterprise App ID/Engine ID: {Style.RESET}").strip()
            if not app_id_input:
                log_error("Engine/App ID cannot be empty.")
                sys.exit(1)

            parsed = parse_gemini_enterprise_app_id(app_id_input)
            if parsed:
                project_number = parsed["project_number"]
                location = parsed["location"]
                collection = parsed["collection"]
                engine_id = parsed["engine_id"]
            else:
                # Construct from short ID
                if not project_number:
                    project_number = input(f"{Style.CYAN}GCP Project Number: {Style.RESET}").strip()
                    if not project_number:
                        log_error("Project number is required.")
                        sys.exit(1)
                
                location = input(f"{Style.CYAN}Location/Region [global]: {Style.RESET}").strip() or "global"
                collection = "default_collection"
                engine_id = app_id_input

            # Construct the full App ID
            full_app_id = f"projects/{project_number}/locations/{location}/collections/{collection}/engines/{engine_id}"

        log_success(f"Targeting App ID: {Style.BOLD}{full_app_id}{Style.RESET}")

        base_endpoint = get_discovery_engine_endpoint(location)
        agents_url = (
            f"{base_endpoint}/v1alpha/{full_app_id}/"
            "assistants/default_assistant/agents"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-goog-user-project": project_number,
            "User-Agent": "google-agents-cli/delete-script"
        }

        # Fetch registered agents
        log_info("Fetching registered agents in the app...")
        try:
            response_data = make_request(agents_url, headers)
            agents = response_data.get("agents", [])
        except Exception as e:
            log_error(f"Failed to fetch agents: {e}")
            sys.exit(1)

        for agent in agents:
            agents_to_display.append({
                "api_object": agent,
                "name": agent.get("name"),
                "app_id": engine_id,
                "location": location,
                "project_number": project_number
            })

    elif find_choice == "2":
        # Creator Flow: Search audit logs
        if not project_id:
            project_id = input(f"{Style.CYAN}GCP Project ID (required for audit logs): {Style.RESET}").strip()
            if not project_id:
                log_error("GCP Project ID is required.")
                sys.exit(1)

        default_email = get_current_user_email()
        if default_email:
            creator_email = input(f"{Style.CYAN}Creator Email [{default_email}]: {Style.RESET}").strip() or default_email
        else:
            creator_email = input(f"{Style.CYAN}Creator Email: {Style.RESET}").strip()
            if not creator_email:
                log_error("Creator email is required.")
                sys.exit(1)

        lookback = input(f"{Style.CYAN}Lookback period (e.g., 7d, 30d, 90d, 400d) [30d]: {Style.RESET}").strip() or "30d"
        raw_agent_names = fetch_agents_by_creator(project_id, creator_email, lookback)
        if not raw_agent_names:
            log_warning(f"No creation history found in audit logs for '{creator_email}' in project '{project_id}' with lookback '{lookback}'.")
            sys.exit(0)

        log_info(f"Checking status of {len(raw_agent_names)} found agent resource(s)...")
        for agent_name in raw_agent_names:
            details = fetch_agent_details(agent_name, access_token)
            if details:
                parts = agent_name.split("/")
                proj_num = parts[1]
                loc = parts[3]
                eng_id = parts[7]
                
                agents_to_display.append({
                    "api_object": details,
                    "name": agent_name,
                    "app_id": eng_id,
                    "location": loc,
                    "project_number": proj_num
                })

    if not agents_to_display:
        log_warning("No active registered agents found with your current selection criteria.")
        sys.exit(0)

    log_banner("Registered Agents matching selection")
    print_agent_list(agents_to_display)

    # Prompt selection
    while True:
        try:
            sel_input = input(f"{Style.CYAN}Select an agent to delete (1-{len(agents_to_display)}) [or 'q' to quit]: {Style.RESET}").strip()
            if sel_input.lower() == 'q':
                log_info("Operation cancelled.")
                sys.exit(0)
            
            sel_idx = int(sel_input)
            if 1 <= sel_idx <= len(agents_to_display):
                selected_item = agents_to_display[sel_idx - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(agents_to_display)}")
        except ValueError:
            print("Invalid input. Please enter a valid number or 'q'.")

    agent_name = selected_item["name"]
    display_name = selected_item["api_object"].get("displayName", "N/A")
    short_agent_id = agent_name.split("/")[-1]

    log_warning(f"You are about to delete agent {Style.BOLD}'{display_name}'{Style.RESET} (ID: {short_agent_id}) from Gemini Enterprise.")
    confirm = input(f"{Style.RED}{Style.BOLD}Are you absolutely sure you want to delete this agent? (y/N): {Style.RESET}").strip()
    if confirm.lower() != 'y':
        log_info("Deletion cancelled.")
        sys.exit(0)

    # Perform DELETE request on the correct region endpoint
    base_endpoint = get_discovery_engine_endpoint(selected_item["location"])
    delete_url = f"{base_endpoint}/v1alpha/{agent_name}"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-goog-user-project": selected_item["project_number"],
        "User-Agent": "google-agents-cli/delete-script"
    }
    
    log_info(f"Sending DELETE request to {delete_url}...")
    try:
        make_request(delete_url, headers, method="DELETE")
        log_success(f"Agent '{display_name}' was successfully deleted/unregistered!")
    except Exception as e:
        log_error(f"Failed to delete agent: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
