import styles from '../../../shared/city-visual-styles.json' with {type:'json'};
export type CityVisualStyle=(typeof styles)['milton-keynes'];
export function cityVisualStyle(city:string):CityVisualStyle|null{return (styles as Record<string,CityVisualStyle>)[city]||null}
