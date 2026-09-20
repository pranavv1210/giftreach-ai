import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import httpx
from .config import get_settings

ROLE_WORDS=("hr","human resources","people","employee engagement","administration","admin","procurement","workplace","talent","culture","career","recruit","hiring")
EMAIL_RE=re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",re.I)
class ProviderUnavailable(RuntimeError): pass

@dataclass
class CompanyFinding:
    name:str; domain:str; website:str; source_url:str; evidence:str; query:str
@dataclass
class ContactFinding:
    email:str; source_url:str; description:str; confidence:float; source_type:str="PUBLICLY_LISTED"

class BraveDiscoveryProvider:
    name="brave"
    def __init__(self,client=None): self.client=client or httpx.Client(timeout=15,follow_redirects=True,headers={"User-Agent":"GiftReachResearch/1.0"})
    def search(self,query,count=10):
        key=get_settings().brave_search_api_key or get_settings().search_api_key
        if not key: raise ProviderUnavailable("Brave Search is not configured. Set BRAVE_SEARCH_API_KEY.")
        r=self.client.get("https://api.search.brave.com/res/v1/web/search",params={"q":query,"count":min(count,20),"country":"IN","search_lang":"en"},headers={"X-Subscription-Token":key,"Accept":"application/json"})
        r.raise_for_status();return r.json().get("web",{}).get("results",[])
    def discover_companies(self,queries,limit):
        seen=set();findings=[];blocked=("linkedin.com","facebook.com","instagram.com","youtube.com","wikipedia.org","justdial.com")
        for query in queries:
            for result in self.search(query,min(limit,20)):
                url=result.get("url","");host=urlparse(url).netloc.lower().removeprefix("www.")
                if not host or any(x in host for x in blocked) or host in seen:continue
                seen.add(host);title=re.split(r"[|–—-]",unescape(result.get("title",host)))[0].strip()
                findings.append(CompanyFinding(title or host,host,f"https://{host}",url,result.get("description","")[:1000],query))
                if len(findings)>=limit:return findings
        return findings

class OfficialWebsiteContactProvider:
    name="official_website"
    def __init__(self,client=None): self.client=client or httpx.Client(timeout=12,follow_redirects=True,headers={"User-Agent":"GiftReachResearch/1.0"})
    def discover(self,website,limit=3):
        parsed=urlparse(website if "://" in website else "https://"+website);origin=f"{parsed.scheme}://{parsed.netloc}";host=parsed.netloc.lower().removeprefix("www.")
        pages=[origin,urljoin(origin,"/contact"),urljoin(origin,"/contact-us"),urljoin(origin,"/about"),urljoin(origin,"/team"),urljoin(origin,"/careers"),urljoin(origin,"/jobs"),urljoin(origin,"/people")]
        found={};visited=set();robots=RobotFileParser()
        try:
            rr=self.client.get(urljoin(origin,"/robots.txt"));robots.set_url(urljoin(origin,"/robots.txt"));robots.parse(rr.text.splitlines() if rr.status_code==200 else [])
        except httpx.HTTPError:robots.parse([])
        try:
            sm=self.client.get(urljoin(origin,"/sitemap.xml"))
            if sm.status_code==200:
                for loc in re.findall(r"<loc>\s*([^<]+)\s*</loc>",sm.text,re.I):
                    if self._candidate_link(loc,host):pages.append(unescape(loc.strip()))
        except httpx.HTTPError:pass
        index=0
        while index<len(pages) and len(visited)<15 and len(found)<limit:
            url=pages[index];index+=1
            if url in visited or not robots.can_fetch("GiftReachResearch/1.0",url):continue
            visited.add(url)
            try:
                r=self.client.get(url)
                if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""):continue
                text=unescape(r.text[:2_000_000]);lower=text.lower()
                for href in re.findall(r'href=["\']([^"\'#]+)',text,re.I):
                    link=urljoin(str(r.url),unescape(href.strip()))
                    if self._candidate_link(link,host) and link not in visited and link not in pages:pages.append(link)
                for email in EMAIL_RE.findall(text):
                    email=email.lower().strip(".,;:>")
                    if email.split("@")[-1].removeprefix("www.")!=host:continue
                    pos=lower.find(email);context=lower[max(0,pos-120):pos+len(email)+120];local=email.split("@")[0]
                    relevant=any(w in context or w in local for w in ROLE_WORDS)
                    if relevant and email not in found:
                        recruitment=any(w in local or w in context for w in ("career","careers","jobs","recruit","hiring"))
                        kind="PUBLIC_RECRUITMENT" if recruitment else "PUBLICLY_LISTED"
                        confidence=.45 if recruitment else .7
                        description="Public recruitment inbox on the official company website; role relevance requires founder review" if recruitment else "Public HR, People, Administration, or Procurement inbox on the official company website"
                        found[email]=ContactFinding(email,str(r.url),description,confidence,kind)
                    if len(found)>=limit:return list(found.values())
            except (httpx.HTTPError,ValueError):continue
        return list(found.values())
    @staticmethod
    def _candidate_link(url,host):
        p=urlparse(url);link_host=p.netloc.lower().removeprefix("www.")
        if link_host!=host:return False
        path=(p.path+"?"+p.query).lower()
        return any(word in path for word in ("contact","career","job","people","team","about","human-resource","hr","talent","culture","procurement","admin"))

class OverpassDiscoveryProvider:
    name="overpass"
    def __init__(self,client=None):self.client=client or httpx.Client(timeout=45,follow_redirects=True,headers={"User-Agent":"GiftReachAI/1.0 (owner-operated business research)"})
    def discover_companies(self,campaign,limit):
        locations=campaign.cities or campaign.districts or ["Bengaluru"];findings=[];seen=set()
        for location in locations[:3]:
            safe=re.sub(r'[^A-Za-z0-9 ._-]','',location)
            query=f'[out:json][timeout:30];area["name"="{safe}"]["boundary"="administrative"]->.a;(nwr(area.a)["name"]["website"]["office"];nwr(area.a)["name"]["website"]["company"];nwr(area.a)["name"]["contact:website"]["office"];);out tags center {min(limit,100)};'
            r=self.client.post(get_settings().overpass_api_url,data={"data":query});r.raise_for_status()
            for item in r.json().get("elements",[]):
                tags=item.get("tags",{});website=tags.get("website") or tags.get("contact:website");name=tags.get("name")
                if not website or not name:continue
                if not website.startswith(("http://","https://")):website="https://"+website
                host=urlparse(website).netloc.lower().removeprefix("www.")
                if not host or host in seen:continue
                seen.add(host);osm_url=f"https://www.openstreetmap.org/{item.get('type')}/{item.get('id')}"
                findings.append(CompanyFinding(name,host,website,osm_url,f"OpenStreetMap business record in {location}",f"OpenStreetMap: {location}"))
                if len(findings)>=limit:return findings
        return findings

def campaign_queries(campaign):
    locations=campaign.cities or campaign.districts or ["Bengaluru"];industries=campaign.industries or ["company","business"]
    return [f'{industry} companies in {location} Karnataka official website' for location in locations for industry in industries[:5]][:10]
