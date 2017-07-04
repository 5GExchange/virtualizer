find . -name "*.yang" -type f -exec pyang -f tree -o {}.tree {} \;
rename -f 's/.yang.tree$/.tree/' *.tree
