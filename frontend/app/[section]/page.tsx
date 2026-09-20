import Dashboard from '@/components/Dashboard';
export default async function Section({params}:{params:Promise<{section:string}>}){const {section}=await params;return <Dashboard section={section}/>}
