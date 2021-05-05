[[NATS.io](http://nats.io/)] ([http://nats.io/](http://nats.io/)) is a high performance messaging system written in Golang. NATS is very easy to use, has very high bandwidth, easily scales. Has 48 well-known clients, 11 of which are supported by the maintainers and 18 are contributors to the community. Delivery guarantees, high availability and fault tolerance. NATS is used on the web, IoT, and blockchains.

### **Subject**

Subject in NATS is like topic in Kafka or url in http server. At its simplest, a subject is just a string of characters that form a name the publisher and subscriber can use to find each other.

Text below is taken from official [NATS docs](https://docs.nats.io/) 

### Subject Hierarchies

For example, a world clock application might define the following to logically group related subjects:

```jsx

time.us
time.us.east
time.us.east.atlanta
time.eu.east
time.eu.warsaw
```

### Wildcards

NATS provides two *wildcards* that can take the place of one or more elements in a dot-separated subject. Subscribers can use these wildcards to listen to multiple subjects with a single subscription but Publishers will always use a fully specified subject, without the wildcard.

### Matching A Single Token

The first wildcard is `*` which will match a single token. For example, if an application wanted to listen for eastern time zones, they could subscribe to `time.*.east`, which would match `time.us.east` and `time.eu.east`.

![https://gblobscdn.gitbook.com/assets%2F-LqMYcZML1bsXrN3Ezg0%2F-LqMZac7AGFpQY7ewbGi%2F-LqMZftc5Yt_LEI224RE%2Fsubjects2.svg?alt=media](https://gblobscdn.gitbook.com/assets%2F-LqMYcZML1bsXrN3Ezg0%2F-LqMZac7AGFpQY7ewbGi%2F-LqMZftc5Yt_LEI224RE%2Fsubjects2.svg?alt=media)

### Matching Multiple Tokens

The second wildcard is `>` which will match one or more tokens, and can only appear at the end of the subject. For example, `time.us.>` will match `time.us.east` and `time.us.east.atlanta`, while `time.us.*` would only match `time.us.east` since it can't match more than one token.

![https://gblobscdn.gitbook.com/assets%2F-LqMYcZML1bsXrN3Ezg0%2F-LqMZac7AGFpQY7ewbGi%2F-LqMZfteO4zWGmIbkFHf%2Fsubjects3.svg?alt=media](https://gblobscdn.gitbook.com/assets%2F-LqMYcZML1bsXrN3Ezg0%2F-LqMZac7AGFpQY7ewbGi%2F-LqMZfteO4zWGmIbkFHf%2Fsubjects3.svg?alt=media)

### Monitoring and Wire Taps

Subject to your security configuration, wildcards can be used for monitoring by creating something sometimes called a *wire tap*. In the simplest case you can create a subscriber for `>`. This application will receive all messages -- again, subject to security settings -- sent on your NATS cluster.

### Mix Wildcards

The wildcard `*` can appear multiple times in the same subject. Both types can be used as well. For example, `*.*.east.>`will receive `time.us.east.atlanta`.