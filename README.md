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

## Detailed Usage

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
* **Gowalla**: A 4D dataset consisting of $6,442,892$ latitude-longitude points of check-ins 
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

### License

All code is provided as-is under the *Apache License 2.0*. See
[`LICENSE`](./LICENSE) for full license text.