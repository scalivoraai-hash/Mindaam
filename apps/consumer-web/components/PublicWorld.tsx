import Link from 'next/link';
import {useState,type ReactNode} from 'react';

const districts = [
  ['milton-keynes', 'Milton Keynes', 'Whitehouse'],
  ['london', 'London', 'Soho'],
  ['dubai', 'Dubai', 'United Arab Emirates'],
  ['new-york', 'New York', 'United States'],
  ['kochi', 'Kochi', 'India'],
];

const streets:Record<string,string> = {
  "kochi": "M377.0 218.5 L247.5 207.5 L228.0 203.0 L185.0 193.5",
  "dubai": "M14.5 69.0 L17.0 69.0 L19.0 68.5 L21.0 68.0 L23.0 67.5 L25.5 68.0 L28.0 68.0 L59.0 75.0 L74.0 78.5 L75.5 78.5 L77.0 78.5 L78.5 78.0 L80.0 77.5 L81.0 77.0 L81.5 76.0 L85.0 69.5 L86.0 69.0 L87.0 68.5 L88.5 68.0 L90.0 68.0",
  "london": "M61.0 84.5 L59.5 106.0 L59.5 108.0 L59.5 110.0 L61.0 117.0 L61.0 117.5 L61.0 118.0 L65.5 145.5 L65.5 146.5 L65.5 147.5 L70.5 162.0 L71.0 163.0 L71.0 164.0 L74.0 170.5 L74.5 171.0 L75.0 171.5 L75.5 172.0 L81.5 171.5 L84.5 171.0 L129.5 169.5",
  "new-york": "M178.5 157.0 L156.5 154.0 L145.0 153.0 L97.5 147.0 L87.0 145.5 L84.0 145.5 L67.0 143.5 L53.0 141.5 L46.5 140.5 L44.0 140.0 L42.0 139.0 L40.5 138.5 L39.0 138.0 L37.5 137.5 L36.5 136.5 L35.0 135.5 L34.5 134.5 L32.5 130.5 L31.0 121.0",
  "milton-keynes": "M313.5 69.0 L302.5 66.5 L276.5 61.5 L263.0 59.5 L241.5 56.0 L206.5 51.5 L201.0 51.0 L156.5 48.5 L144.0 49.0 L126.5 49.5 L98.5 51.0 L96.0 51.5 L58.5 56.0 L35.0 59.5"
};

export default function PublicWorld({children, enabled}: {children:ReactNode; enabled:string[]}) {
  const [selected,setSelected]=useState(0);
  const [id,name,place]=districts[selected];
  return <div className="public-world">
    <div className="world-arrival">
      <div className="arrival-sky" aria-hidden="true"><i/><i/><i/></div>
      <section className="arrival-copy"><h1>A Living World.<br/><em>Together.</em></h1>
        <p>Explore real-inspired cities. Meet people. Walk, drive, chat and experience moments together in a living 3D social world.</p>
        <div className="arrival-actions"><a className="primary" href="#enter-mindaam">Enter Mindaam</a><Link className="arrival-preview" href="/explore">Preview the World ↗</Link></div>
      </section>
      <div className="arrival-auth" id="enter-mindaam" tabIndex={-1}>{children}</div>
    </div>
    <section className="district-showcase"><h2>Pick a district to explore</h2>
      <div className="district-film">
        <figure><svg viewBox="0 0 400 230" role="img" aria-label={name+' mapped street illustration'}>
          <image href={'/art/districts/'+id+'.webp'} width="400" height="230"/>
          <g className="district-travellers" key={id}>
            <g><rect x="-3.5" y="-2" width="7" height="4" rx="1" fill="#e2a56a"/><animateMotion path={streets[id]} dur="11s" repeatCount="indefinite" rotate="auto"/></g>
            <g><circle cy="-2" r="1.8" fill="#fad0aa"/><path d="M0 0v4m0-1-1.8 3m1.8-3 2 3" stroke="#74e0d1" strokeWidth="1.8"/><animateMotion path={streets[id]} dur="25s" repeatCount="indefinite"/></g>
          </g>
        </svg><figcaption>{place} · Map illustration © OpenStreetMap contributors</figcaption></figure>
        <div className="district-choices" aria-label="Choose a district illustration">{districts.map(([key,title,area],index)=>
          <button key={key} type="button" aria-pressed={index===selected} onClick={()=>setSelected(index)}><strong>{title}</strong><small>{area} · {enabled.includes(key)?'Enabled · account access applies':enabled.length?'Currently unavailable':'Checking availability…'}</small></button>)}</div>
      </div>
    </section>
    <section className="public-experiences"><h2>Meet in the world</h2><div>
      <article><h3>Out on the streets</h3><p>Explore cities, walk with friends, collect XP and ride local transport.</p></article>
      <article><h3>Face to face</h3><p>Customise your avatar, meet new people and connect through voice and video chat.</p></article>
      <article><h3>Take the stage</h3><p>Host free events and concerts in virtual auditoriums. Invite friends and share your screen.</p></article>
    </div></section>
    <section className="public-journey"><h2>How Mindaam works</h2><ol>{['Create your account','Choose your city','Enter the 3D world','Explore, meet and connect','Host experiences and invite friends'].map(step=><li key={step}>{step}</li>)}</ol></section>
    <aside className="public-future"><h2>Coming soon</h2><p>Build and customise a virtual home, own or rent spaces and create branded business locations.</p></aside>
    <section className="arrival-final"><h2>Your city. Your people. Your world.</h2><a className="primary" href="#enter-mindaam">Step Into Mindaam</a> <Link href="/explore">Preview the World</Link></section>
  </div>;
}
