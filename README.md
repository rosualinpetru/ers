# Range Search on Encrypted Multi-Attribute Data: Experiment Code (Extensions)

This fork implements additional range search schemes for multi-attribute data.

*The only contribution is contained in the **extensions** package!*

* **ers**: The package contains schemes associated with the paper "Range Search on Encrypted Multi-Attribute Data" by Francesca Falzon, Evangelia Anna Markatou, Zachary Espiritu, and Roberto Tamassia.
* **extensions**: Contains newly introduced schemes.

**Important:** This repository implements several cryptographic primitives (used for research purposes) which should not be used in production.

## Dependencies 

Our schemes assume prior installation of Python 3.12.0 or above which can be installed from [here](https://www.python.org/downloads/source/).
The `requirements.txt` file in the main directory contains a list of all the necessary dependencies for running our schemes and reproducing our experiments; these dependencies can be installed using the `pip3 install -r requirements.txt` command.

## Detailed Usage

### Benchmarking the schemes

We additionally implement the following schemes:

* **Hilbert**: A scheme that achieves optimal storage at the expense of query bandwidth.

Each of our schemes can be tested on the following four datasets:

* **Spitz**:  A 2D dataset of $28,837$ latitude-longitude points of phone location data of politician Malte Spitz from Aug 2009 to Feb 2010.
* **NH**: A 3D dataset comprised of $4,096$ elevation points on domain $[2^6] \times [2^6] \times [2^6]$ sampled from the United States Geological Survey's Elevation Data from the White Mountains of New Hampshire. We change the domain size by keeping exactly one aggregated elevation value per latitude and longitude value. 
* **Gowalla**: A 4D dataset consisting of $6,442,892$ latitude-longitude points of check-ins 
 from users of the  Gowalla social networking website  between  2009 and 2010.
* **Cali**: A 2D dataset of $21,047$ latitude-longitude points of road network intersections in California.

You can execute our schemes on these datasets by executing the following command from the root directory of the repository:

```
$ bash {spitz.sh, cali.sh, gowalla.sh, nh.sh} {hilbert}
```

For example, if you wish to reproduce our Hilbe scheme experiments on the California data set, then you should run `$ bash cali.sh range_brc`. Each such command generates builds the index over the appropriate domain size and reports the resulting index size and setup time. Then it generates 100 queries and averages and reports the query response times and query sizes over these 100 queries.

### License

All code is provided as-is under the *Apache License 2.0*. See
[`LICENSE`](./LICENSE) for full license text.

The source code from the `extensions` should be prefixed with a comment containing the following text:

```
Copyright 2024 Alin-Petru Rosu and Evangelia Anna Markatou

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
