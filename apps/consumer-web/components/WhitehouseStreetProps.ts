import type {Object3D} from 'three';
import {bench, box, tree} from './WorldAssets';
import nodes from './whitehouseStreetNodes.json';

// Mapped point locations © OpenStreetMap contributors, ODbL 1.0.
// Source IDs and survey limitations are retained in current-map-comparison.json.
// Build before spatial batching, so ornaments add no gameplay entities or colliders.
export function addWhitehouseStreetProps(district:Object3D){
 for(const [kind,px,pz,source] of nodes){
  const x=Number(px), z=Number(pz);
  switch(kind){
   case 'tree': tree(district,x,z,Number(source)); break;
   case 'bench': bench(district,x,z); break;
   case 'bus_stop':
    box(district,'#515c61',x,1.4,z,.065,2.8,.065);
    box(district,'#f0d760',x+.17,2.56,z,.43,.36,.06);
    box(district,'#e5e6e0',x,1.4,z,.22,.34,.08);
    break;
   case 'street_lamp':
    box(district,'#55636a',x,2.5,z,.13,5,.13);
    box(district,'#f5efcf',x+.25,5,z,.65,.13,.3);
    break;
   case 'waste_basket':
    box(district,'#31473f',x,.45,z,.52,.9,.5);
    box(district,'#202a27',x,.85,z+.25,.32,.12,.02);
    break;
   case 'post_box':
    box(district,'#a03332',x,.66,z,.45,1.32,.43);
    box(district,'#282a28',x,1.01,z+.22,.31,.055,.03);
    break;
   case 'grit_bin':
    box(district,'#bf9b3d',x,.35,z,.95,.7,.59);
    box(district,'#d4b352',x,.72,z,1.02,.08,.65);
    break;
  }
 }
}
