# Range Search on Encrypted Multi-Attribute Data: Experiment Code

This fork implements additional range search schemes for multi-attribute data and refactors the existing code.

Packages:

* **ers.structures**: Defines structures that generically handle any number of dimensions.
* **ers.schemes**: The package contains schemes associated with the paper "Range Search on Encrypted Multi-Attribute Data" by Francesca Falzon, Evangelia Anna Markatou, Zachary Espiritu, and Roberto Tamassia. These schemes are refactored to handle any dimension generically.
* **ers.benchmark**: Contains utilities to generate XLSX reports, generate datasets and plot Hilbert schemes.

**Important:** This repository implements several cryptographic primitives (used for research purposes) which should not be used in production.

## Dependencies 

Our schemes assume prior installation of Python 3.12.0 or above which can be installed from [here](https://www.python.org/downloads/source/).
The `requirements.txt` file in the main directory contains a list of all the necessary dependencies for running our schemes and reproducing our experiments; these dependencies can be installed using the `pip3 install -r requirements.txt` command.

## Scheme Design

An **Encrypted Multi-Map (EMM)** scheme securely indexes multi-dimensional data to enable efficient and confidential range queries. At its core, an EMM provides secure storage and retrieval functionalities, allowing clients to query encrypted data without revealing the queries or the data to the storage provider.

The main functionalities of an EMM scheme include:

1. **Setup**:
   - Generates cryptographic keys required for encryption, indexing, and query processing.

2. **Index Construction**:
   - Data points are securely indexed by encrypting and storing them in a structured format. This involves mapping multi-dimensional data into suitable representations (such as hyperranges or hyperrectangles) and securely storing these representations using cryptographic primitives.

3. **Trapdoor Generation**:
   - Produces secure search tokens (trapdoors) for querying encrypted data. A trapdoor ensures that the query remains confidential, and only authorized parties with the secret key can create valid search tokens.

4. **Search Operation**:
   - Processes queries using the generated trapdoors, searching the encrypted index without decrypting it. The search identifies encrypted results matching the query parameters while preserving confidentiality.

5. **Result Resolution**:
   - Decrypts the encrypted results returned from the search operation. Only entities holding the correct cryptographic keys can perform this step, ensuring confidentiality and integrity of the retrieved data.

All implemented schemes follow this general EMM structure, differing primarily in their specific indexing strategies and data representation methods.

## Hilbert Schemes

### Benchmarking the schemes

The benchmark script is able to detect the number of dimensions of a specified dataset and instantiate the scheme according to the number of dimensions.

The schemes that were implemented, but were generalised to any dimension:
* **Linear** - could be seen as a tree of depth 1, where all leafs are points in the domain
* **RangeBRC** - uses multi-dimensional trees. As implementation, a multi-dimensional tree is implemented as a product of HyperTrees (trees of decomposing HyperRanges / HyperRectangles) where each tree in the product is one dimensional and each dimension is represented by a tree. The division is performed on each invididual tree/dimension and the results (descending operations, range covers, etc.) are reconstructed by doing a product between the partial results of each dimension.
* **TdagSRC** - same as RangeBRC, but the division strategy is different, i.e., each dimension upon being split in two, also inserts an overlapping middle segments between the middles of the splits, for each dimension.
* **QuadBRC** - simply decomposes a HyperRange into smaller Ranges by dividing each dimension in two. Depending on the number of dimensions, the resulting number of decomposed ranges can be different: (number_of_splits)^(number_of_dimensions).
* **QuadSRC** - same as QuadBRC, but uses SRC.

For better understanding how the HyperRange, HyperTree, HyperTreeProduct and RangeDividers work, please refer to the documentation in the code.

The schemes that are additionally implemented:
* LinearHilbert
* RangeBRCHilbert - since a Hilbert curve reduces dimensionality to 1, the RangeBRCHilbert would represent a HyperTreeProduct with only one tree. Therefore, RangeBRCHilbert relies only on a HyperTree that divides the Hilbert curve in half recursively.
* TdagSRCHilbert - same as RangeBRCHilbert, but uses a different division strategy with middle overlap.
* QuadBRCHilbert - equivalent to QuadBRC. Split a HyperTree in 2^(number_of_dimensions) in order to keep the height of the tree constant. Records the same index size as QuadBRC.
* QuadSRCHilbert - same as QuadBRCHilbert, but uses SRC.

The Hilbert curve is used in the first step to first map the domain (points) to Hilbert domain (Hilbert indices). Then, BRC and SRC are defined for a Hilbert curve, including how to determine the segments that form a HyperRange with some empirical parameters to trade-off efficiency, precision and security. Refer to the Hilbert curve data structure in the code for more details about how it functions.

Each of our schemes can be tested on the following four datasets:

* **Spitz**:  A 2D dataset of $28,837$ latitude-longitude points of phone location data of politician Malte Spitz from Aug 2009 to Feb 2010.
* **NH**: A 3D dataset comprised of $4,096$ elevation points on domain $[2^6] \times [2^6] \times [2^6]$ sampled from the United States Geological Survey's Elevation Data from the White Mountains of New Hampshire. We change the domain size by keeping exactly one aggregated elevation value per latitude and longitude value. 
* **Gowalla**: A 2D dataset consisting of $6,442,892$ latitude-longitude points of check-ins 
 from users of the  Gowalla social networking website  between  2009 and 2010.
* **Cali**: A 2D dataset of $21,047$ latitude-longitude points of road network intersections in California.
* **Dense 2D**: A generated 2D dataset that covers the entire domain, up to a specified number of records.

To run a benchmark, run a script specific for each dataset:
* cali.sh # Domain size should be in $[2^0]$ to $[2^{15}]$ as increasing the scale beyond brings no difference.
* nh.sh
* spitz.sh # Domain size should be in $[2^0]$ to $[2^{16}]$ as increasing the scale beyond brings no difference.
* gowalla.sh (takes a lot of time) # Domain size should be in $[2^0]$ to $[2^{42}]$ as increasing the scale beyond brings no difference.

The code currently takes the original datasets and can map the points to a specified domain size. The domain size is parametrized.
It is advisable to read and configure the script before running the benchmark.
For instance, to run spitz:
```commandline
for d in $(seq 6 6); do
  python3 -m ers.benchmark.cli \
    --scheme "$SCHEME" \
    --dataset spitz \
    --domain-size $d \
    --records-limit 1000000 \
    --queries-count $QUERIES_COUNT
done
```
**d** represents the dimension size as bit length. You can configure the range such that multiple
domain sizes are benchmarked sequentially (this is to submit a longer job for a server to handle).
The benchmark output will be in the **benchmarks** folder.

### Observations

* The Linear and LinearHilbert schemes are equivalent in terms of security and index size; can be proven trivially. Still they differ in computational efficiency as the schemes differ in the algorithm by which they traverse all points within a query bounding box (HyperRange). LinearHilbert appears to be faster when the query is large and there are multiple dimensions. 
* The QuadBRC, QuadSRC and QuadBRCHilbert, QuadSRCHilbert, respectively, are equivalent in terms of security and index size. This is because the way Quad schemes recursively divide a HyperRange is equivalent to the construction of the Hilbert curves. In other words, the index built by all four schemes are equivalent (for splitting always in half, the number of nodes being the of geometric progression with a = 1, r = 2^d, n = d + 1, where d is dimensions) with the only difference being the representation of the range within a node (former schemes define ranges as bounding boxes, while the latter by a contiguous Hilbert segment).
* The RangeBRC, TdagSRC and RangeBRCHilbert, TdagSRCHilbert, respectively, are NOT equivalent in terms of security and index size. This is because the Hilbert versions do not index ranges that are not represented by a single, **contiguous** Hilbert segment. The intuition is give by the following example: Consider a 2D domain space of size 2, represented by the HyperRange (0,0) X (3,3) the corresponding Hilbert curve, and a splitting in half strategy. In RangeBRC the multi-dimensional tree indexes the HyperRange (0,0) X (3,1), whereas the Hilbert versions do not because this is represented by two discontinuous Hilbert segments: [0, 3] and [12, 15].

## Data-dependent schemes

The previously described schemes use deterministic index constructions, meaning they follow fixed strategies for indexing data, independent of the specific dataset. Consequently, deterministic schemes do not require clients to store additional metadata when generating search tokens.

In contrast, **data-dependent schemes** adapt their indexing strategy based on the actual distribution and density of the data. Rather than uniformly dividing the domain, these schemes create an index tailored specifically to the dataset. Such constructions have the potential to improve query performance and efficiency when data distributions are highly skewed or uneven.

A data-dependent scheme involves:

- **Analyzing Data Density**: The scheme computes the density distribution of points across different dimensions within the dataset.

- **Adaptive Division of Domain**: The scheme attempts to divide the domain dynamically in approximately even distributed subdivisions.

See the implementation in the ("CustomDataDependentSplitDivider").

This adaptive indexing approach usually requires the client to retain additional information or state, as the search trapdoors must be consistent with the specific dataset-dependent index structure.

Nevertheless, it should be important to note that if the index becomes data-dependent, so should the queries. In other words, we would use data-dependent schemes knowing that particular queries have a higher probability of being asked on the specific dataset (e.g., considering age and a medical condition, it might be the case that a particular age range is associated with a particular medical condition, dependently).

### License

All code is provided as-is under the *Apache License 2.0*. See
[`LICENSE`](./LICENSE) for full license text.