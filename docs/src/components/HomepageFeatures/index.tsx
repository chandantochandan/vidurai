import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  Svg: React.ComponentType<React.ComponentProps<'svg'>>;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Three-Kosha Architecture',
    Svg: require('@site/static/img/logo.svg').default,
    description: (
      <>
        Inspired by Vedantic philosophy, Vidurai implements a three-layer memory system:
        working memory (Annamaya), episodic memory (Manomaya), and permanent wisdom (Vijnanamaya).
      </>
    ),
  },
  {
    title: 'RL-Based Compression',
    Svg: require('@site/static/img/logo.svg').default,
    description: (
      <>
        The Vismriti RL Agent learns optimal compression strategies through reinforcement learning,
        automatically balancing token costs with information quality.
      </>
    ),
  },
  {
    title: 'Easy Integration',
    Svg: require('@site/static/img/logo.svg').default,
    description: (
      <>
        Works seamlessly with LangChain, LlamaIndex, and custom AI applications.
        Simple API with powerful memory management capabilities.
      </>
    ),
  },
];

function Feature({title, Svg, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <Svg className={styles.featureSvg} role="img" />
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
