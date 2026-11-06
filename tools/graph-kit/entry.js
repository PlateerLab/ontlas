// What the page's graph needs, as one file: the renderer, the graph model and the layouts.
import Graph from 'graphology';
import louvain from 'graphology-communities-louvain';
import { circlepack, circular, random } from 'graphology-layout';
import force from 'graphology-layout-force';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import noverlap from 'graphology-layout-noverlap';
import Sigma from 'sigma';
import { animateNodes } from 'sigma/utils';
import { createEdgeCurveProgram, indexParallelEdgesIndex } from '@sigma/edge-curve';
import { createNodeBorderProgram } from '@sigma/node-border';

window.GraphKit = {
  Graph, Sigma, animateNodes, createEdgeCurveProgram, createNodeBorderProgram, indexParallelEdgesIndex, louvain,
  layouts: { circlepack, circular, force, forceAtlas2, noverlap, random },
};
