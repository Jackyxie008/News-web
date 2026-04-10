import React from 'react';

import styles from './index.module.scss';

const Component = () => {
  return (
    <div className={styles.search2}>
      <p className={styles.value}>搜索</p>
      <div className={styles.search}>
        <div className={styles.icon} />
      </div>
    </div>
  );
}

export default Component;
