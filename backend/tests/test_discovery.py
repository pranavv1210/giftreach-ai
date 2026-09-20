from app.providers import CompanyFinding,ContactFinding,ProviderUnavailable
from app.worker import process_one

def campaign(client,auth):
    r=client.post("/api/discovery-campaigns",headers=auth,json={"name":"Bengaluru HR search","cities":["Bengaluru"],"districts":["Bengaluru Urban"],"industries":["Software"],"contact_roles":["HR Manager"],"max_companies":5,"max_contacts_per_company":3,"provider":"brave","generate_drafts":True})
    assert r.status_code==201;return r.json()

def test_campaign_creation_and_missing_provider_is_honest(client,auth):
    c=campaign(client,auth)
    client.patch("/api/agent",headers=auth,json={"mode":"RESEARCH"})
    assert client.post(f"/api/discovery-campaigns/{c['id']}/start",headers=auth).status_code==200
    assert process_one() is True
    jobs=client.get(f"/api/jobs?campaign_id={c['id']}",headers=auth).json()
    assert jobs[0]["status"]=="PENDING"
    assert "BRAVE_SEARCH_API_KEY" in jobs[0]["error_message"]

def test_autonomous_pipeline_dedupes_and_builds_review_queue(client,auth,monkeypatch):
    from app import worker
    monkeypatch.setattr(worker.BraveDiscoveryProvider,"discover_companies",lambda self,queries,limit:[CompanyFinding("Real Test Co","real.example","https://real.example","https://search.example/result","Official result for Real Test Co",queries[0])])
    monkeypatch.setattr(worker.OfficialWebsiteContactProvider,"discover",lambda self,website,limit:[ContactFinding("hr@real.example","https://real.example/contact","Listed on official contact page",.65)])
    c=campaign(client,auth);client.patch("/api/agent",headers=auth,json={"mode":"DRAFT"});client.post(f"/api/discovery-campaigns/{c['id']}/start",headers=auth)
    assert process_one();assert process_one();assert process_one()
    review=client.get(f"/api/review?campaign_id={c['id']}",headers=auth).json()
    assert len(review)==1
    assert review[0]["company"]=="Real Test Co"
    assert review[0]["email"]=="hr@real.example"
    assert review[0]["source_type"]=="PUBLICLY_LISTED"
    assert review[0]["draft_status"]=="DRAFT"
    assert review[0]["eligible"] is False
    assert len(client.get("/api/companies",headers=auth).json())==1
    assert len(client.get("/api/contacts",headers=auth).json())==1

def test_discovery_researches_official_website_not_evidence_page(client,auth,monkeypatch):
    from app import worker
    researched=[]
    monkeypatch.setattr(worker.OverpassDiscoveryProvider,"discover_companies",lambda self,c,l:[CompanyFinding("Mapped Co","mapped.example","https://mapped.example","https://www.openstreetmap.org/node/1","Mapped business", "OpenStreetMap: Bengaluru")])
    monkeypatch.setattr(worker.OfficialWebsiteContactProvider,"discover",lambda self,website,limit:researched.append(website) or [])
    r=client.post("/api/discovery-campaigns",headers=auth,json={"name":"Free search","provider":"overpass","max_companies":1})
    client.patch("/api/agent",headers=auth,json={"mode":"RESEARCH"});client.post(f"/api/discovery-campaigns/{r.json()['id']}/start",headers=auth)
    process_one();process_one()
    assert researched==["https://mapped.example"]
    company=client.get("/api/companies",headers=auth).json()[0]
    assert company["source_url"]=="https://mapped.example"
    assert "openstreetmap.org/node/1" in company["evidence"]
    assert company["industry"] is None

def test_bulk_approval_and_send_preview_excludes_unverified(client,auth,monkeypatch):
    from app import worker
    monkeypatch.setattr(worker.BraveDiscoveryProvider,"discover_companies",lambda self,q,l:[CompanyFinding("Acme","acme.example","https://acme.example","https://source.example","Evidence",q[0])])
    monkeypatch.setattr(worker.OfficialWebsiteContactProvider,"discover",lambda self,w,l:[ContactFinding("people@acme.example","https://acme.example/team","Public listing",.7)])
    c=campaign(client,auth);client.patch("/api/agent",headers=auth,json={"mode":"DRAFT"});client.post(f"/api/discovery-campaigns/{c['id']}/start",headers=auth)
    process_one();process_one();process_one();item=client.get("/api/review",headers=auth).json()[0]
    approved=client.post("/api/review/bulk/approve",headers=auth,json={"draft_ids":[item["draft_id"]]})
    assert approved.status_code==200 and approved.json()["approved"]==[item["draft_id"]]
    plan=client.post("/api/review/bulk/preview-send",headers=auth,json={"draft_ids":[item["draft_id"]]}).json()
    assert plan["eligible"]==[]
    assert "not verified" in plan["excluded"][0]["reasons"][0]
    assert client.post("/api/review/bulk/send",headers=auth,json={"draft_ids":[item["draft_id"]],"provider":"mock","confirm":False}).status_code==422

def test_cancel_persistent_jobs(client,auth):
    c=campaign(client,auth);client.patch("/api/agent",headers=auth,json={"mode":"RESEARCH"});client.post(f"/api/discovery-campaigns/{c['id']}/start",headers=auth)
    cancelled=client.post(f"/api/discovery-campaigns/{c['id']}/cancel",headers=auth)
    assert cancelled.json()["status"]=="CANCELLED"
    assert client.get(f"/api/jobs?campaign_id={c['id']}",headers=auth).json()[0]["status"]=="CANCELLED"
