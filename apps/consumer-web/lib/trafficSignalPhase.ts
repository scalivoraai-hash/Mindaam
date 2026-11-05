/** Shared-clock scenery cycle. Never controls the authoritative driving simulation. */
export function trafficSignalPhase(seconds:number,axis:0|1):'red'|'amber'|'green'{
 const time=((seconds%50)+50)%50;
 if(axis===0){if(time<19)return 'green';if(time<22)return 'amber';return 'red'}
 if(time>=25&&time<44)return 'green';if(time>=44&&time<47)return 'amber';return 'red';
}
