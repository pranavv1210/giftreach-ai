def test_auth_required(client):
    assert client.get("/api/overview").status_code==401
    assert client.post("/api/auth/login",json={"email":"owner@example.com","password":"bad"}).status_code==401

def add_company(client,auth,name="Acme Karnataka"):
    r=client.post("/api/companies",headers=auth,json={"name":name,"industry":"Software","size":"Mid-sized","city":"Bengaluru","district":"Bengaluru Urban","source_url":"https://example.com","evidence":"Official website lists a Bengaluru office"})
    assert r.status_code==201;return r.json()

def add_contact(client,auth,company,email="hr@example.com",name="Asha"):
    r=client.post("/api/contacts",headers=auth,json={"company_id":company["id"],"name":name,"email":email,"title":"People Operations Manager","source_type":"Founder-provided","source_description":"Entered by founder"})
    assert r.status_code==201;return r.json()

def test_complete_mock_outreach_and_idempotency(client,auth):
    company=add_company(client,auth);contact=add_contact(client,auth,company)
    assert contact["verification_status"]=="SYNTAX_VALID"
    assert contact["sources"][0]["source_type"]=="Founder-provided"
    draft=client.post("/api/drafts",headers=auth,json={"contact_id":contact["id"]}).json()
    assert draft["validation_errors"]==[]
    same=client.post("/api/drafts",headers=auth,json={"contact_id":contact["id"]}).json()
    assert same["id"]==draft["id"]
    assert client.post(f"/api/drafts/{draft['id']}/approve",headers=auth).status_code==200
    assert client.post(f"/api/drafts/{draft['id']}/send",headers=auth).status_code==409
    client.post(f"/api/contacts/{contact['id']}/verify-manually",headers=auth)
    client.patch("/api/agent",headers=auth,json={"mode":"CONTROLLED_AUTOPILOT","sending_paused":False})
    sent=client.post(f"/api/drafts/{draft['id']}/send",headers=auth)
    assert sent.status_code==200 and sent.json()["provider"]=="mock"
    again=client.post(f"/api/drafts/{draft['id']}/send",headers=auth)
    assert again.json()["message_id"]==sent.json()["message_id"]

def test_multiple_contacts_and_suppression(client,auth):
    company=add_company(client,auth)
    a=add_contact(client,auth,company,"one@example.com","One")
    b=add_contact(client,auth,company,"two@example.com","Two")
    assert len(client.get("/api/contacts",headers=auth).json())==2
    d=client.post("/api/drafts",headers=auth,json={"contact_id":b["id"]}).json()
    client.post(f"/api/drafts/{d['id']}/approve",headers=auth)
    client.post(f"/api/contacts/{b['id']}/verify-manually",headers=auth)
    client.post(f"/api/contacts/{b['id']}/suppress",headers=auth)
    client.patch("/api/agent",headers=auth,json={"mode":"CONTROLLED_AUTOPILOT","sending_paused":False})
    assert client.post(f"/api/drafts/{d['id']}/send",headers=auth).status_code==409

def test_policy_blocks_unapproved_category(client,auth):
    company=add_company(client,auth);contact=add_contact(client,auth,company)
    d=client.post("/api/drafts",headers=auth,json={"contact_id":contact["id"]}).json()
    bad=client.patch(f"/api/drafts/{d['id']}",headers=auth,json={"subject":"Gift options","body":"Hello, we sell chocolates.\n\nPranav V.\nCorporate Gifting\nPlease decline."})
    assert bad.json()["validation_errors"]
    assert client.post(f"/api/drafts/{d['id']}/approve",headers=auth).status_code==422

def test_kill_switch_prevents_send(client,auth):
    company=add_company(client,auth);contact=add_contact(client,auth,company)
    d=client.post("/api/drafts",headers=auth,json={"contact_id":contact["id"]}).json()
    client.post(f"/api/drafts/{d['id']}/approve",headers=auth);client.post(f"/api/contacts/{contact['id']}/verify-manually",headers=auth)
    client.patch("/api/agent",headers=auth,json={"mode":"CONTROLLED_AUTOPILOT","sending_paused":False})
    client.post("/api/agent/emergency-stop",headers=auth)
    assert client.post(f"/api/drafts/{d['id']}/send",headers=auth).status_code==409

