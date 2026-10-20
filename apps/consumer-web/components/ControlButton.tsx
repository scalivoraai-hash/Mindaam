'use client';
import {ButtonHTMLAttributes,ReactNode} from 'react';
export default function ControlButton({label,children,className='',...props}:ButtonHTMLAttributes<HTMLButtonElement>&{label:string;children:ReactNode}){
 return <button type="button" {...props} className={'control-button '+className} aria-label={label} title={label}>{children}<span className="control-tooltip" aria-hidden="true">{label}</span></button>;
}
