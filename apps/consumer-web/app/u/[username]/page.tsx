'use client';
import {useParams} from 'next/navigation';
import Link from 'next/link';
import {UserProfile} from '@/components/UserProfile';
export default function ProfilePage(){const params=useParams<{username:string}>();return <main className="profile-page"><Link href="/">← Back to Mindaam</Link><UserProfile username={params.username}/><p>Sign in to Mindaam to view permitted profiles and connect.</p></main>}
